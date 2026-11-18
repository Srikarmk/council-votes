"""The two public sources of Boston City Council roll-call votes, fetched politely and cached as raw files.

- Analyze Boston, the City's open data portal: a dataset of every councillor's vote on every roll call
  from January 2008 to March 2024, public domain (Open Data Commons PDDL). Read through its CKAN API.
- boston.gov's roll-call search page: the same records, still updated, one HTML page of entries at a time.
  The City's terms of use expect third parties to republish City information; robots.txt allows these
  pages. Requests are spaced out, and only pages that may have changed are fetched again.

Raw responses are kept in data/raw/, so every parsed record can be traced to what the City published.
"""

from __future__ import annotations

import glob
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


def shifted_dir() -> str:
    return os.path.join(RAW, "bostongov", "shifted")


def _entries(html: str) -> dict[str, str]:
    """A saved page's roll-call entries by boston.gov node id, each as its verbatim HTML."""
    from bs4 import BeautifulSoup
    out = {}
    for node in BeautifulSoup(html, "html.parser").select("div.node-roll-call-dockets"):
        nid = next((c[5:] for c in node.get("class", []) if re.fullmatch(r"node-\d+", c)), "")
        if nid:
            out[nid] = str(node)
    return out


def keep_shifted(old: dict[int, str], stamp: str) -> int:
    """Save the entries of overwritten pages that no saved page holds any more. Returns how many.

    The roll-call pager lists the newest first, so each new roll call pushes every older one down. A run that
    refetches only the newest pages overwrites page N with entries that used to be on page N-1, and the
    entries that slid from page N to page N+1 are now in neither the fresh page N nor the old page N+1. They
    go to shifted/, which the build reads after the pages.
    """
    present = set()
    for path in glob.glob(os.path.join(RAW, "bostongov", "page-*.html")):
        present |= set(_entries(open(path).read()))
    for path in glob.glob(os.path.join(shifted_dir(), "*.html")):
        present |= set(_entries(open(path).read()))
    kept = 0
    for n, html in sorted(old.items()):
        lost = {nid: e for nid, e in _entries(html).items() if nid not in present}
        if not lost:
            continue
        os.makedirs(shifted_dir(), exist_ok=True)
        with open(os.path.join(shifted_dir(), f"page-{n:04d}-{stamp}.html"), "w") as f:
            f.write(f"<!-- {ROLLCALL_URL}: entries that were on page {n} before a refetch moved them -->\n")
            f.write("\n".join(lost.values()) + "\n")
        present |= set(lost)
        kept += len(lost)
    return kept


def fetch_rollcall_pages(pages: list[int], delay: float = DELAY) -> list[int]:
    """Fetch boston.gov roll-call pages (0 is the newest) into data/raw/bostongov/. Returns the pages saved.

    A 503 or other server error stops the run instead of retrying in a loop: boston.gov's own outage page
    is not data, and the next scheduled run will try again. Entries that an overwrite would lose go to
    shifted/ (see keep_shifted), including when the run stops partway.
    """
    saved = []
    old: dict[int, str] = {}
    os.makedirs(os.path.dirname(page_path(0)), exist_ok=True)
    try:
        with _client() as c:
            for i, n in enumerate(pages):
                if i:
                    time.sleep(delay)
                r = _get(c, n)
                if r.status_code != 200 or "node-roll-call-dockets" not in r.text:
                    raise SourceError(f"boston.gov page {n}: HTTP {r.status_code}, no roll-call entries in the reply")
                if os.path.exists(page_path(n)):
                    old[n] = open(page_path(n)).read()
                with open(page_path(n), "w") as f:
                    f.write(keep(r.text))
                saved.append(n)
    finally:
        kept = keep_shifted(old, time.strftime("%Y%m%d", time.gmtime()))
        if kept:
            print(f"boston.gov: kept {kept} entr{'y' if kept == 1 else 'ies'} that moved past the refetched pages")
    return saved


def _get(c: httpx.Client, n: int, tries: int = 3) -> httpx.Response:
    """One page, retrying a dropped connection or a timeout (seen on long runs) with a growing pause."""
    for attempt in range(tries):
        try:
            return c.get(ROLLCALL_URL, params={"page": n} if n else None)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            if attempt == tries - 1:
                raise SourceError(f"boston.gov page {n}: {type(e).__name__} after {tries} tries") from e
            time.sleep(10 * (attempt + 1))
    raise AssertionError("unreachable")


def keep(html: str) -> str:
    """The part of a roll-call page worth keeping, verbatim: each roll-call entry and the pager. The rest
    (menus, scripts, per-request tokens) would make every fetch differ from the last."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    entries = [str(n) for n in soup.select("div.node-roll-call-dockets")]
    pager = sorted(set(re.findall(r"[?&]page=(\d+)", html)), key=int)
    links = "".join(f'<a href="?page={p}"></a>' for p in pager)
    return f"<!-- {ROLLCALL_URL}: roll-call entries and pager, as published -->\n" + "\n".join(entries) + f"\n<nav>{links}</nav>\n"


def last_page(html: str) -> int:
    """The highest page number in a roll-call page's pager."""
    return max((int(x) for x in re.findall(r"[?&]page=(\d+)", html)), default=0)
