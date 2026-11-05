"""Parse boston.gov roll-call pages and the open dataset into one shape: a roll call with its votes.

A roll call is one recorded vote of the Council: a docket number, a meeting date, the clerk's description
of the motion and its outcome, and how each councillor voted. Nothing is inferred here; cleaning (names,
vote codes) happens in clean.py, where every change is logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class RollCall:
    source: str             # "bostongov" or "opendata"
    source_id: str          # boston.gov node id, or the dataset's roll_call_id
    docket: str             # as published, e.g. "0424"
    date: str               # YYYY-MM-DD
    description: str
    votes: list[tuple[str, str]] = field(default_factory=list)  # (councillor as published, vote as published)


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else ""


def parse_rollcall_page(html: str) -> list[RollCall]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for node in soup.select("div.node-roll-call-dockets"):
        node_id = next((c[5:] for c in node.get("class", []) if re.fullmatch(r"node-\d+", c)), "")
        docket = re.sub(r"^Docket\s*#\s*", "", _text(node.select_one(".dr-t")))
        t = node.select_one("time[datetime]")
        date = t["datetime"][:10] if t else ""
        desc = _text(node.select_one(".g--7 p")) or _text(node.select_one(".g--7"))
        desc = re.sub(r"^Description:\s*", "", desc)
        votes = []
        for v in node.select(".paragraph--type--roll-call-vote"):
            name, vote = _text(v.select_one(".g--8")), _text(v.select_one(".g--4"))
            if name:
                votes.append((name.rstrip(":").strip(), vote))
        if node_id and date:
            out.append(RollCall("bostongov", node_id, docket, date, desc, votes))
    return out


def parse_opendata(rows: list[dict]) -> list[RollCall]:
    by_id: dict[str, RollCall] = {}
    for r in sorted(rows, key=lambda r: int(r["_id"])):
        rid = str(r["roll_call_id"])
        rc = by_id.get(rid)
        if rc is None:
            rc = by_id[rid] = RollCall("opendata", rid, str(r["docket_number"] or "").strip(),
                                       str(r["vote_date"])[:10], (r["subject"] or "").strip())
        rc.votes.append(((r["councillor"] or "").strip(), (r["vote"] or "").strip()))
    return list(by_id.values())
