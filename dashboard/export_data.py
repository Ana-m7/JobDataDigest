"""Export a Power-BI-ready star schema from jobdatadigest.db.

Why export CSVs instead of pointing Power BI straight at the SQLite file:
Power BI Desktop has no native SQLite connector (it would need an ODBC
driver installed separately), while "Get Data > Text/CSV" works with zero
setup on any machine. The exported files are a fact table (postings) and a
bridge table (posting_skills) for the one genuinely many-to-many
relationship -- the same star-schema shape used inside the SQLite DB itself,
just flattened to CSV.

Raw description text is deliberately excluded: it isn't used by any planned
visual, and leaving it out keeps the export small and avoids shipping full
job-posting text into a BI file.

Usage:
    python -m dashboard.export_data
"""

import sqlite3

import pandas as pd

from cleaning.config import DB_PATH, PROJECT_ROOT

EXPORT_DIR = PROJECT_ROOT / "dashboard" / "data"


def run() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        postings = pd.read_sql_query(
            """
            SELECT posting_id, title, company, primary_role, city, state, seniority,
                   category, contract_type, contract_time, salary_min, salary_max,
                   salary_avg, has_salary, description_length, created_date, redirect_url,
                   pull_date
            FROM postings
            """,
            conn,
        )
        posting_skills = pd.read_sql_query("SELECT posting_id, skill FROM posting_skills", conn)
    finally:
        conn.close()

    postings.to_csv(EXPORT_DIR / "postings.csv", index=False)
    posting_skills.to_csv(EXPORT_DIR / "posting_skills.csv", index=False)

    print(f"Exported {len(postings)} postings -> {EXPORT_DIR / 'postings.csv'}")
    print(f"Exported {len(posting_skills)} posting-skill rows -> {EXPORT_DIR / 'posting_skills.csv'}")


if __name__ == "__main__":
    run()
