"""Normalization rules for turning raw Adzuna pulls into the postings table."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "jobdatadigest.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

# Adzuna doesn't recognize "Delhi NCR" as a single searchable place, so
# ingestion queried "Delhi" and "Gurgaon" separately (see ingestion/config.py).
# We reconcile them into one metro area here, at cleaning time, since for
# analysis purposes a Gurgaon posting and a Delhi posting are both "NCR".
CITY_NORMALIZATION = {
    "Delhi": "Delhi NCR",
    "Gurgaon": "Delhi NCR",
}

# When a posting's title/description matches more than one role search
# (477 of ~4,858 unique postings did, in the first pull), we have to pick one
# "primary_role" for simple per-role queries and charts. We resolve ties by
# specificity: a posting matching both "Data Scientist" and the very generic
# "Software Engineer" query is more informatively labeled "Data Scientist",
# since broad titles are the ones most likely to catch incidental matches.
# Listed most specific (highest priority) to least specific.
ROLE_PRIORITY = [
    "Machine Learning Engineer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Business Analyst",
    "Software Engineer",
]

# Adzuna's free-tier "description" field is hard-truncated; verified empirically
# (max observed length across 5,401 pulled records was exactly this value).
DESCRIPTION_TRUNCATION_LENGTH = 500

# Below this, a salary figure is almost certainly a data-entry error rather
# than a real annual CTC -- e.g. a monthly stipend or hourly rate mistakenly
# entered in the annual field. Verified by inspection: postings under this
# threshold in the first pull included things like "Data Entry internship"
# at INR 2,000-5,000 and "Software Engineer" at INR 78/173 (clearly not
# annual pay). Affected ~1.3% of salaried postings in the first pull.
MIN_PLAUSIBLE_ANNUAL_SALARY_INR = 100_000
