"""The two public sources of Boston City Council roll-call votes, fetched politely and cached as raw files.

- Analyze Boston, the City's open data portal: a dataset of every councillor's vote on every roll call
  from January 2008 to March 2024, public domain (Open Data Commons PDDL). Read through its CKAN API.
- boston.gov's roll-call search page: the same records, still updated, one HTML page of entries at a time.
  The City's terms of use expect third parties to republish City information; robots.txt allows these
  pages. Requests are spaced out, and only pages that may have changed are fetched again.

Raw responses are kept in data/raw/, so every parsed record can be traced to what the City published.
"""

from __future__ import annotations

import json
import os
import re
import time

import httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw")

USER_AGENT = "council-votes/0.1 (a non-commercial civic project; github.com/Srikarmk/council-votes)"
OPENDATA_RESOURCE = "e41f49ac-5233-487e-976c-3c2d8f6e1c8e"
OPENDATA_API = "https://data.boston.gov/api/3/action/datastore_search"
ROLLCALL_URL = "https://www.boston.gov/departments/city-council/city-council-roll-call-votes"
DELAY = 3.0  # seconds between boston.gov requests
FIELDS = ["_id", "roll_call_id", "docket_number", "subject", "vote_date", "councillor", "vote"]


class SourceError(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)


def fetch_opendata(path: str | None = None) -> list[dict]:
    """Every row of the open dataset, paged through the API, saved to data/raw/opendata.json."""
    path = path or os.path.join(RAW, "opendata.json")
    rows, offset = [], 0
    with _client() as c:
        while True:
            r = c.get(OPENDATA_API, params={"resource_id": OPENDATA_RESOURCE, "limit": 5000, "offset": offset})
            r.raise_for_status()
            res = r.json()["result"]
            rows += [{k: r.get(k) for k in FIELDS} for r in res["records"]]  # drop the API's search index
            offset += len(res["records"])
            if not res["records"] or offset >= res["total"]:
                break
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f, ensure_ascii=False)
    return rows


def page_path(n: int) -> str:
    return os.path.join(RAW, "bostongov", f"page-{n:04d}.html")


def fetch_rollcall_pages(pages: list[int], delay: float = DELAY) -> list[int]:
    """Fetch boston.gov roll-call pages (0 is the newest) into data/raw/bostongov/. Returns the pages saved.

    A 503 or other server error stops the run instead of retrying in a loop: boston.gov's own outage page
    is not data, and the next scheduled run will try again.
    """
    saved = []
    os.makedirs(os.path.dirname(page_path(0)), exist_ok=True)
    with _client() as c:
        for i, n in enumerate(pages):
            if i:
                time.sleep(delay)
            r = c.get(ROLLCALL_URL, params={"page": n} if n else None)
            if r.status_code != 200 or "node-roll-call-dockets" not in r.text:
                raise SourceError(f"boston.gov page {n}: HTTP {r.status_code}, no roll-call entries in the reply")
            with open(page_path(n), "w") as f:
                f.write(r.text)
            saved.append(n)
    return saved


def last_page(html: str) -> int:
    """The highest page number in a roll-call page's pager."""
    return max((int(x) for x in re.findall(r"[?&]page=(\d+)", html)), default=0)
