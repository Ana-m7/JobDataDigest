"""Export a small data snapshot for the deployed Streamlit app.

Why this file is committed while the rest of data/ is gitignored: Streamlit
Community Cloud deploys straight from this GitHub repo and has no access to
your local SQLite database, your Adzuna API key, or raw pulls -- all of
which are (correctly) gitignored. Without *some* committed data, the
deployed app would have nothing to show.

The compromise: commit a small, fully-derived snapshot (~4,900 rows of
aggregated posting metadata and skill tags, no raw description text, nothing
that wasn't already going to be public once analyzed) purely so the live
demo works for anyone visiting the deployed URL. The real pipeline --
ingestion with your own API key, cleaning, NLP extraction -- still runs
entirely from source, gitignored data included; this snapshot is a
deployment convenience, not a substitute for it.

Usage:
    python -m app.export_app_data
"""

import sqlite3

import pandas as pd

from cleaning.config import DB_PATH, PROJECT_ROOT

EXPORT_DIR = PROJECT_ROOT / "app" / "data"


def run() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        postings = pd.read_sql_query(
            """
            SELECT posting_id, primary_role, city, seniority, salary_avg, has_salary,
                   description_length, pull_date
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
