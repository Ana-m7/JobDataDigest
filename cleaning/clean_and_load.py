"""Clean raw Adzuna pulls and load them into the SQLite analytics store.

Design note: this script is idempotent by rebuild, not by upsert. Every run
wipes and rebuilds `postings` / `posting_roles` from whatever raw JSON
currently exists under data/raw/. That keeps the database a pure derived
view of the raw layer -- if a cleaning rule turns out to be wrong, we fix it
here and re-run, rather than trying to patch already-loaded rows.

Usage:
    python -m cleaning.clean_and_load
"""

from __future__ import annotations

import glob
import json
import sqlite3
from collections import defaultdict

from cleaning.config import (
    CITY_NORMALIZATION,
    DB_PATH,
    DESCRIPTION_TRUNCATION_LENGTH,
    MIN_PLAUSIBLE_ANNUAL_SALARY_INR,
    RAW_DATA_DIR,
    ROLE_PRIORITY,
    SCHEMA_PATH,
)
from nlp.seniority import infer_seniority


def normalize_city(city_query: str) -> str:
    return CITY_NORMALIZATION.get(city_query, city_query)


def pick_primary_role(roles_matched: set) -> str:
    for role in ROLE_PRIORITY:
        if role in roles_matched:
            return role
    return sorted(roles_matched)[0]  # defensive fallback; shouldn't trigger


def compute_salary_avg(salary_min, salary_max):
    """Returns (salary_min, salary_max, salary_avg, has_salary), nulling out
    figures below MIN_PLAUSIBLE_ANNUAL_SALARY_INR -- see config.py for why."""
    if salary_min and salary_max:
        avg = (salary_min + salary_max) / 2
    else:
        avg = salary_min or salary_max or None

    if avg is not None and avg < MIN_PLAUSIBLE_ANNUAL_SALARY_INR:
        return None, None, None, 0

    has_salary = int(bool(salary_min or salary_max))
    return salary_min, salary_max, avg, has_salary


def extract_state(location: dict) -> str | None:
    area = location.get("area") or []
    # area is ["India", "<state>", "<city>", ...]; state is index 1 when present.
    return area[1] if len(area) > 1 else None


def load_raw_records():
    """Read every raw pull and collapse duplicate postings into one record each.

    A posting can legitimately appear under more than one role search (see
    ROLE_PRIORITY docstring in config.py), so we accumulate the *set* of
    roles matched per posting_id while keeping one canonical copy of the
    posting's own fields (they're identical across role matches -- same job).
    """
    postings = {}          # posting_id -> dict of cleaned scalar fields
    roles_by_posting = defaultdict(set)
    pull_date_by_posting = {}

    files = glob.glob(str(RAW_DATA_DIR / "*" / "*.json"))
    for path in files:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)

        role_query = payload["role_query"]
        pull_date = payload["pulled_at"][:10]

        for r in payload["raw_response"].get("results", []):
            posting_id = r["id"]
            roles_by_posting[posting_id].add(role_query)

            # Later pulls of the same posting overwrite earlier ones, so the
            # stored row always reflects the most recent time we saw it.
            existing_pull_date = pull_date_by_posting.get(posting_id)
            if existing_pull_date and existing_pull_date > pull_date:
                continue
            pull_date_by_posting[posting_id] = pull_date

            location = r.get("location", {})
            description = r.get("description", "")
            salary_min, salary_max, salary_avg, has_salary = compute_salary_avg(
                r.get("salary_min"), r.get("salary_max")
            )

            postings[posting_id] = {
                "posting_id": posting_id,
                "title": r.get("title"),
                "company": (r.get("company") or {}).get("display_name"),
                "description": description,
                "description_length": len(description),
                "description_truncated": int(len(description) >= DESCRIPTION_TRUNCATION_LENGTH),
                "seniority": infer_seniority(r.get("title"), description),
                "location_raw": location.get("display_name"),
                "city": normalize_city(payload["city_query"]),
                "state": extract_state(location),
                "category": (r.get("category") or {}).get("label"),
                "contract_type": r.get("contract_type"),
                "contract_time": r.get("contract_time"),
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_avg": salary_avg,
                "has_salary": has_salary,
                "created_date": r.get("created"),
                "redirect_url": r.get("redirect_url"),
                "pull_date": pull_date,
            }

    for posting_id, row in postings.items():
        row["primary_role"] = pick_primary_role(roles_by_posting[posting_id])

    return postings, roles_by_posting


def build_database(postings: dict, roles_by_posting: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM posting_roles")
        conn.execute("DELETE FROM postings")

        columns = [
            "posting_id", "title", "company", "description", "description_length",
            "description_truncated", "primary_role", "seniority", "location_raw", "city",
            "state", "category", "contract_type", "contract_time", "salary_min", "salary_max",
            "salary_avg", "has_salary", "created_date", "redirect_url", "pull_date",
        ]
        placeholders = ", ".join(f":{c}" for c in columns)
        conn.executemany(
            f"INSERT INTO postings ({', '.join(columns)}) VALUES ({placeholders})",
            postings.values(),
        )

        role_rows = [
            (posting_id, role)
            for posting_id, roles in roles_by_posting.items()
            for role in roles
        ]
        conn.executemany(
            "INSERT INTO posting_roles (posting_id, role) VALUES (?, ?)", role_rows
        )
        conn.commit()
    finally:
        conn.close()


def print_summary(postings: dict) -> None:
    rows = list(postings.values())
    total = len(rows)
    with_salary = sum(r["has_salary"] for r in rows)
    truncated = sum(r["description_truncated"] for r in rows)

    by_role = defaultdict(int)
    by_city = defaultdict(int)
    by_seniority = defaultdict(int)
    for r in rows:
        by_role[r["primary_role"]] += 1
        by_city[r["city"]] += 1
        by_seniority[r["seniority"]] += 1

    print(f"Loaded {total} unique postings into {DB_PATH}")
    print(f"  with salary disclosed: {with_salary} ({with_salary/total:.1%})")
    print(f"  description truncated at {DESCRIPTION_TRUNCATION_LENGTH} chars: {truncated} ({truncated/total:.1%})")
    print("  by primary_role:")
    for role, count in sorted(by_role.items(), key=lambda kv: -kv[1]):
        print(f"    {role}: {count}")
    print("  by city:")
    for city, count in sorted(by_city.items(), key=lambda kv: -kv[1]):
        print(f"    {city}: {count}")
    print("  by seniority (inferred):")
    for seniority, count in sorted(by_seniority.items(), key=lambda kv: -kv[1]):
        print(f"    {seniority}: {count} ({count/total:.1%})")


def run() -> None:
    postings, roles_by_posting = load_raw_records()
    build_database(postings, roles_by_posting)
    print_summary(postings)


if __name__ == "__main__":
    run()
