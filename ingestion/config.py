"""Configuration for the Adzuna ingestion pipeline: what to pull and how."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = "in"
ADZUNA_BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search"

ROLES = [
    "Data Analyst",
    "Business Analyst",
    "Software Engineer",
    "Data Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
]

# Adzuna geocodes free-text location strings. "Delhi NCR" is not a real place
# name Adzuna recognizes well, so we search "Delhi" and "Gurgaon" separately
# and treat both as part of the NCR region during cleaning (Step 2).
CITIES = [
    "Bangalore",
    "Mumbai",
    "Pune",
    "Hyderabad",
    "Delhi",
    "Gurgaon",
    "Chennai",
]

RESULTS_PER_PAGE = 50  # Adzuna's max per page

# Free tier is rate-limited (~250 calls/day). 6 roles x 7 cities x 3 pages
# = 126 calls per run, leaving headroom for retries within the daily cap.
MAX_PAGES_PER_COMBO = 3
REQUEST_DELAY_SECONDS = 1.2  # stay under ~1 req/sec

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
