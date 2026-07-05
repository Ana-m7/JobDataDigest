"""Infer a seniority band (Junior / Mid / Senior / Unknown) from posting text.

Why this step exists: Adzuna's `what` search is free-text over title +
description, not an experience-level filter. A search for "Data Analyst"
returns fresher postings and "Senior Data Analyst, 8+ years" postings alike.
Verified on this dataset: 17.3% of titles contain the word "senior" outright.
So "seniority" has to be inferred after the fact if we want to separate
fresher-relevant postings from senior ones in analytics (Step 4) and the ML
model (Step 5).

Rule priority (most to least reliable signal):
  1. An explicit years-of-experience mention near the word "experience"/"exp"
     (e.g. "3-5 years of experience"). This is the most direct signal when
     present, so it wins over keyword guessing when both exist.
       0-1 years  -> Junior
       2-4 years  -> Mid
       5+  years  -> Senior
  2. Seniority keywords in the TITLE. Titles are short and purpose-written,
     so a title word carries real signal.
  3. A restricted keyword set in the DESCRIPTION, as a fallback. "lead" and
     "manager" are deliberately excluded here (but not from title-matching)
     because in body text they very often describe something other than the
     posting's own seniority -- "lead generation" (common in Business
     Analyst / sales-adjacent postings) and "reports to the manager" both
     contain the word without indicating a senior role.
  4. Otherwise: Unknown. This is a real, kept category -- about half of
     postings state no seniority signal at all, and we'd rather say "we
     don't know" than fabricate a label. Unknown postings are excluded from
     seniority-conditioned analysis and from the ML model's training set.

This inference is itself a source of noise (same class of limitation as the
skill extraction in extract_skills.py): keyword rules can't perfectly
capture intent, and a very small number of postings will be mislabeled.
"""

from __future__ import annotations

import re

_YEARS_EXPERIENCE = re.compile(
    r"(?:(\d{1,2})\s*(?:-|to|\+)?\s*(\d{1,2})?\+?\s*years?[^.]{0,25}?exp)"
    r"|(?:exp[^.]{0,25}?(\d{1,2})\s*(?:-|to|\+)?\s*(\d{1,2})?\+?\s*years?)",
    re.IGNORECASE,
)

_TITLE_SENIOR_KEYWORDS = re.compile(
    r"\bsenior\b|\bsr\.?\b|\blead\b|\bprincipal\b|\bstaff\b|\bmanager\b", re.IGNORECASE
)
_DESCRIPTION_SENIOR_KEYWORDS = re.compile(
    r"\bsenior\b|\bsr\.?\b|\bprincipal\b|\bstaff\b", re.IGNORECASE
)
_JUNIOR_KEYWORDS = re.compile(
    r"\bjunior\b|\bjr\.?\b|\bfresher\b|\bentry.level\b|\btrainee\b|\bgraduate\b|\bintern(ship)?\b",
    re.IGNORECASE,
)

_MAX_PLAUSIBLE_YEARS = 20  # guards against unrelated matches like "70-year-old company"


def infer_seniority(title: str, description: str) -> str:
    title = title or ""
    description = description or ""
    combined = f"{title} {description}"

    years_match = _YEARS_EXPERIENCE.search(combined)
    if years_match:
        nums = [int(g) for g in years_match.groups() if g is not None]
        min_years = min(nums)
        if min_years <= _MAX_PLAUSIBLE_YEARS:
            if min_years <= 1:
                return "Junior"
            if min_years <= 4:
                return "Mid"
            return "Senior"

    if _TITLE_SENIOR_KEYWORDS.search(title):
        return "Senior"
    if _JUNIOR_KEYWORDS.search(title):
        return "Junior"

    if _DESCRIPTION_SENIOR_KEYWORDS.search(description):
        return "Senior"
    if _JUNIOR_KEYWORDS.search(description):
        return "Junior"

    return "Unknown"
