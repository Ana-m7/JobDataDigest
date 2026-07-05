"""Thin client around the Adzuna Job Search API with retry/backoff.

Adzuna's free tier can return transient errors (rate limiting, brief 5xx
blips). We retry with exponential backoff instead of failing the whole
pipeline run over one flaky request.
"""

import time

import requests

from ingestion.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_BASE_URL,
    RESULTS_PER_PAGE,
)

MAX_RETRIES = 4
INITIAL_BACKOFF_SECONDS = 2


class AdzunaAPIError(Exception):
    pass


def fetch_page(role: str, city: str, page: int) -> dict:
    """Fetch one page of results for a role/city search.

    Adzuna pages are 1-indexed in the URL path. Returns the parsed JSON
    response, which includes 'count' (total matches) and 'results' (list
    of postings for this page).
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise AdzunaAPIError(
            "Missing ADZUNA_APP_ID / ADZUNA_APP_KEY. Copy .env.example to .env "
            "and fill in your credentials from developer.adzuna.com."
        )

    url = f"{ADZUNA_BASE_URL}/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": role,
        "where": city,
        "content-type": "application/json",
    }

    backoff = INITIAL_BACKOFF_SECONDS
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=20)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429 or response.status_code >= 500:
                last_error = AdzunaAPIError(
                    f"HTTP {response.status_code} on {role}/{city} page {page}: "
                    f"{response.text[:200]}"
                )
            else:
                # 4xx other than 429 (e.g. bad params) won't fix itself on retry.
                raise AdzunaAPIError(
                    f"HTTP {response.status_code} on {role}/{city} page {page}: "
                    f"{response.text[:200]}"
                )

        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2

    raise AdzunaAPIError(
        f"Failed to fetch {role}/{city} page {page} after {MAX_RETRIES} attempts: {last_error}"
    )
