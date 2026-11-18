"""council-votes: fetch the City's roll-call records and build the site's data.

    uv run councilvotes update          # the scheduled run: newest boston.gov pages, the dataset, then build
    uv run councilvotes fetch --all     # every boston.gov page (about 185, three seconds apart)
    uv run councilvotes build           # rebuild web/data from what's already in data/raw
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import build, sources

STATE = os.path.join(sources.RAW, "bostongov", "fetched.json")
STALE_AFTER = timedelta(days=7)  # a week of failed fetches fails the scheduled job, so someone hears about it
NEWEST_PAGES = 3                 # new roll calls appear on page 0; three pages covers a busy month
HEARTBEAT = timedelta(days=3)    # how often a quiet week still records a successful fetch (a small commit)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _state() -> dict:
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def _save_state(**kw) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    s = _state() | kw
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2)
        f.write("\n")


def fetch(pages: list[int] | None) -> bool:
    """Fetch boston.gov pages; returns False (and records the failure) when the site doesn't answer."""
    try:
        if pages is None:
            sources.fetch_rollcall_pages([0])
            last = sources.last_page(open(sources.page_path(0)).read())
            pages = list(range(1, last + 1))
        saved = sources.fetch_rollcall_pages(pages)
    except (sources.SourceError, OSError) as e:
        # Only the log records a failure: writing it to the committed state would commit every day of an outage.
        print(f"boston.gov: {e}", file=sys.stderr)
        return False
    last = _state().get("last_success")
    if not last or _now() - datetime.fromisoformat(last) > HEARTBEAT:
        _save_state(last_success=_now().isoformat(timespec="seconds"))
    print(f"boston.gov: saved {len(saved)} page(s)")
    return True


def _published() -> Counter:
    """The (date, docket) pairs in the site's current data, counted, so a rebuild can be checked against it."""
    path = os.path.join(build.OUT, "rollcalls.json")
    if not os.path.exists(path):
        return Counter()
    return Counter((r["date"], r["docket"].lstrip("0")) for r in json.load(open(path)))


def _outputs() -> dict[str, str | None]:
    """The files a build writes, as they are now, so a bad build can be undone."""
    paths = [os.path.join(build.OUT, n) for n in ("rollcalls.json", "councillors.json", "summary.json")]
    paths.append(os.path.join(build.ROOT, "web", "public", "index.json"))
    return {p: (open(p).read() if os.path.exists(p) else None) for p in paths}


def _restore(saved: dict[str, str | None]) -> None:
    for path, text in saved.items():
        if text is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, "w") as f:
                f.write(text)


def lost_roll_calls(before: Counter, after: Counter) -> list[tuple[str, str]]:
    """Roll calls the previous build had and this one doesn't. Keyed by date and docket, not id, because a roll
    call first known from the dataset keeps its key when boston.gov's copy of it replaces the dataset's."""
    return sorted((before - after).elements())


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="councilvotes", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch boston.gov roll-call pages")
    f.add_argument("--all", action="store_true", help="every page, not just the newest")
    f.add_argument("--pages", type=int, default=NEWEST_PAGES)
    f.add_argument("--start", type=int, default=0, help="with --all, resume from this page")
    sub.add_parser("dataset", help="fetch the Analyze Boston dataset")
    sub.add_parser("build", help="build web/data from data/raw")
    sub.add_parser("update", help="the scheduled run")
    a = p.parse_args(argv)

    if a.cmd == "fetch":
        if a.all and a.start:
            last = sources.last_page(open(sources.page_path(0)).read())
            sys.exit(0 if fetch(list(range(a.start, last + 1))) else 1)
        sys.exit(0 if fetch(None if a.all else list(range(a.pages))) else 1)
    if a.cmd == "dataset":
        print(f"dataset: {len(sources.fetch_opendata())} rows")
        return
    if a.cmd == "build":
        print(json.dumps(build.build(), indent=2))
        return

    before, outputs = _published(), _outputs()
    ok = fetch(list(range(NEWEST_PAGES)))
    try:
        print(f"dataset: {len(sources.fetch_opendata())} rows")
    except Exception as e:  # the dataset hasn't changed since 2024; a failed refresh keeps the saved copy
        print(f"dataset: kept the saved copy ({e})", file=sys.stderr)
    s = build.build()
    print(f"built: {s['roll_calls']} roll calls through {s['latest']}, {s['inconsistent']} contradictions")
    lost = lost_roll_calls(before, _published())
    if lost:
        # A roll call never leaves the record on its own; a rebuild that drops one has a bug. Keep the site's
        # data as it was (the fetched pages are still saved) and fail, so the job doesn't commit the loss.
        _restore(outputs)
        print(f"this build lost {len(lost)} roll call(s) the site had, so the site's data was left as it was: " +
              ", ".join(f"{d} #{k}" for d, k in lost[:20]), file=sys.stderr)
        sys.exit(1)
    if not ok:
        last = _state().get("last_success")
        since = _now() - datetime.fromisoformat(last) if last else None
        if since is None or since > STALE_AFTER:
            print(f"boston.gov has not answered since {last or 'the first run'}; failing so this gets noticed",
                  file=sys.stderr)
            sys.exit(1)
