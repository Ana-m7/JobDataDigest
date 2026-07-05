"""Pull job postings from Adzuna for every (role, city) combination.

Design note: this is written to be re-run on a schedule (e.g. weekly) to
build a time series of the job market, not just a one-off pull. Each run
gets its own dated folder under data/raw/ so old pulls are never
overwritten, and a manifest.csv logs what happened on every run for
auditing (how many postings, any failures, when).

Usage:
    python -m ingestion.run_ingestion
"""

import csv
import json
import time
from datetime import date, datetime, timezone

from ingestion.adzuna_client import AdzunaAPIError, fetch_page
from ingestion.config import (
    CITIES,
    MAX_PAGES_PER_COMBO,
    RAW_DATA_DIR,
    REQUEST_DELAY_SECONDS,
    RESULTS_PER_PAGE,
    ROLES,
)


def slugify(text: str) -> str:
    return text.lower().replace(" ", "_")


def run() -> None:
    pull_date = date.today().isoformat()
    out_dir = RAW_DATA_DIR / pull_date
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    total_postings = 0

    for role in ROLES:
        for city in CITIES:
            postings_seen = 0
            for page in range(1, MAX_PAGES_PER_COMBO + 1):
                status = "ok"
                result_count = 0
                total_matches = None

                try:
                    payload = fetch_page(role, city, page)
                except AdzunaAPIError as exc:
                    status = f"error: {exc}"
                    print(f"[FAIL] {role} / {city} page {page}: {exc}")
                else:
                    results = payload.get("results", [])
                    result_count = len(results)
                    total_matches = payload.get("count")
                    postings_seen += result_count

                    out_file = out_dir / f"{slugify(role)}__{slugify(city)}__page{page}.json"
                    with open(out_file, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "pulled_at": datetime.now(timezone.utc).isoformat(),
                                "role_query": role,
                                "city_query": city,
                                "page": page,
                                "raw_response": payload,
                            },
                            f,
                            ensure_ascii=False,
                        )

                    print(f"[OK] {role} / {city} page {page}: {result_count} postings "
                          f"(total matches reported: {total_matches})")

                manifest_rows.append({
                    "pull_date": pull_date,
                    "role_query": role,
                    "city_query": city,
                    "page": page,
                    "result_count": result_count,
                    "total_matches_reported": total_matches,
                    "status": status,
                })

                total_postings += result_count
                time.sleep(REQUEST_DELAY_SECONDS)

                # Stop paginating this combo early if Adzuna has no more results
                # or we've already pulled everything it reports having.
                if result_count == 0 or (total_matches is not None and postings_seen >= total_matches):
                    break

    manifest_path = out_dir / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\nDone. {total_postings} postings pulled across {len(ROLES)} roles x "
          f"{len(CITIES)} cities. Raw files + manifest saved to {out_dir}")


if __name__ == "__main__":
    run()
