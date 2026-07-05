"""Extract skills from posting text and load them into posting_skills.

Approach: compiled regex phrase-matching against the curated dictionary in
skill_dictionary.py (see that file's docstring for why regex was chosen over
spaCy NER). We match against title + description concatenated, since the
description alone is often enough but the title sometimes carries a skill
the (truncated) description doesn't mention.

Known precision/recall limitations -- stated up front because they directly
affect how much to trust downstream skill-demand numbers:
  - RECALL: Adzuna's free-tier description field is hard-truncated at 500
    characters (~97% of our postings hit this cap). Any skill mentioned only
    in the untruncated tail of the real posting is invisible to us. This
    means our skill counts are a systematic *undercount*, not a random one.
  - RECALL: a curated dictionary only catches skills we thought to list. An
    obscure or newly-popular tool not in SKILL_DICTIONARY will never be
    detected, no matter how it's phrased.
  - PRECISION: keyword matching has no concept of context. "SQL" mentioned
    in "no SQL experience required" still counts as a hit. We accept this
    because manually parsing negation reliably needs much more than regex
    (and most real postings list skills as requirements, not exclusions).
  - PRECISION/RECALL tradeoff by design: short, ambiguous tokens (R, Go) are
    matched case-sensitively to cut false positives, at some cost to recall
    for postings that write them in lowercase.

Usage:
    python -m nlp.extract_skills
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

from cleaning.config import DB_PATH, SCHEMA_PATH
from nlp.skill_dictionary import SKILL_DICTIONARY


def _alias_pattern(alias: str, case_sensitive: bool) -> str:
    escaped = re.escape(alias)
    core = escaped if case_sensitive else f"(?i:{escaped})"
    # Custom boundary (rather than \b) because several aliases end in
    # symbols (C++, C#, .NET) where \b doesn't reliably match.
    return rf"(?<![A-Za-z0-9]){core}(?![A-Za-z0-9])"


def compile_skill_patterns() -> dict[str, re.Pattern]:
    compiled = {}
    for skill, aliases in SKILL_DICTIONARY.items():
        alternation = "|".join(_alias_pattern(alias, cs) for alias, cs in aliases)
        compiled[skill] = re.compile(alternation)
    return compiled


def extract_skills(text: str, compiled_patterns: dict[str, re.Pattern]) -> set[str]:
    return {skill for skill, pattern in compiled_patterns.items() if pattern.search(text)}


def run() -> None:
    compiled_patterns = compile_skill_patterns()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM posting_skills")

        cursor = conn.execute("SELECT posting_id, title, description FROM postings")
        rows = cursor.fetchall()

        skill_rows = []
        zero_skill_postings = 0
        skill_counts = Counter()

        for posting_id, title, description in rows:
            text = f"{title or ''} {description or ''}"
            found = extract_skills(text, compiled_patterns)
            if not found:
                zero_skill_postings += 1
            for skill in found:
                skill_rows.append((posting_id, skill))
                skill_counts[skill] += 1

        conn.executemany(
            "INSERT INTO posting_skills (posting_id, skill) VALUES (?, ?)", skill_rows
        )
        conn.commit()
    finally:
        conn.close()

    total = len(rows)
    print(f"Extracted skills for {total} postings ({len(skill_rows)} posting-skill pairs)")
    print(f"  postings with zero skills detected: {zero_skill_postings} ({zero_skill_postings/total:.1%})")
    print("  top 20 skills overall:")
    for skill, count in skill_counts.most_common(20):
        print(f"    {skill}: {count} ({count/total:.1%} of postings)")


if __name__ == "__main__":
    run()
