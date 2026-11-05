"""Build the site's data from the raw sources: roll calls, councillors and a summary, as JSON in web/data/.

boston.gov's roll-call pages are the primary source where they have been fetched; the open dataset fills
in what they don't cover and is compared with them where both have a roll call (matched on date and
docket number). Every derived number on the site comes from these files.
"""

from __future__ import annotations

import glob
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from . import checks, clean, parse
from .sources import RAW, ROLLCALL_URL, ROOT

OUT = os.path.join(ROOT, "web", "data")
DATASET_URL = "https://data.boston.gov/dataset/city-council-roll-call-votes"
KINDS = ["yes", "no", "present", "abstain", "absent"]


def load_sources() -> tuple[list[parse.RollCall], list[parse.RollCall]]:
    gov = []
    for path in sorted(glob.glob(os.path.join(RAW, "bostongov", "page-*.html"))):
        with open(path) as f:
            gov += parse.parse_rollcall_page(f.read())
    seen, unique = set(), []
    for r in gov:  # a page fetched twice, or an entry that shifted pages between fetches
        if r.source_id not in seen:
            seen.add(r.source_id)
            unique.append(r)
    data_path = os.path.join(RAW, "opendata.json")
    od = parse.parse_opendata(json.load(open(data_path))) if os.path.exists(data_path) else []
    return unique, od


def title(description: str, docket: str) -> str:
    """The motion in a line: the description up to its first full stop, without the procedural opening."""
    t = re.sub(r"\s+", " ", description).strip()
    t = re.sub(rf"^0*{int(docket) if docket.isdigit() else re.escape(docket)}\s+", "", t)
    date = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
    t = re.sub(r"^Councill?ors?\s+[^,]+?\s+called\s+Docket\s*#\s*\d+,\s*", "", t, flags=re.I)
    t = re.sub(r"^Councill?ors?\s+.{0,300}?\boffered the following:?\s*", "", t, flags=re.I)
    t = re.sub(rf"^On the (message and (order|ordinance)|petition|communication|order|report)[^,]*?,?\s*"
               rf"(referred(?: on)?\s+{date},?\s*)?(Docket\s*#\s*\d+,?\s*)?", "", t, flags=re.I)
    t = re.sub(rf"^(referred(?: on)?\s+{date},?\s*)?Docket\s*#\s*\d+,?\s*", "", t, flags=re.I)
    t = re.sub(r"^(message and order|message and ordinance|order)\s+for\s+(your|you)\s+approval,?\s*(an?\s+)?",
               "", t, flags=re.I)
    # "the amount of Two Hundred Thousand Dollars ($200,000.00)" -> "$200,000.00"; the figure is the record's
    words = (r"(?:(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|"
             r"Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|Eighty|Ninety|Hundred|"
             r"Thousand|Million|Billion|and)[\s-]*)+")
    spelled = rf"{words}Dollars(?:\s+and\s+{words}Cents)?"
    t = re.sub(r"\bin the amount of\b", "of", t, flags=re.I)
    t = re.sub(rf"(?:the amount of\s+)?\(?{spelled}\)?\s*\((\$[\d,.]+)\)", r"\1", t, flags=re.I)
    t = re.sub(rf"\((\$[\d,.]+)\)\s*\({spelled}\)", r"\1", t, flags=re.I)
    t = re.sub(r"^Message and (order|ordinance)\s+(?=(to|for|approving|authorizing|declaring|amending)\b)", "",
               t, flags=re.I)
    first = re.split(r"(?<=[a-z0-9)\"”])\.\s+(?=[A-Z])", t, maxsplit=1)[0]
    first = first[0].upper() + first[1:] if first else first
    return first if len(first) <= 180 else first[:177].rsplit(" ", 1)[0] + "…"


def outcome(description: str) -> str:
    """The clerk's closing sentence, which states what happened and the tally."""
    t = re.sub(r"\s+", " ", description).strip()
    parts = re.split(r"(?<=[.;])\s+", t)
    with_tally = [p for p in parts if re.search(r"\byeas?\b", p, flags=re.I)]
    return (with_tally[-1] if with_tally else parts[-1]).strip()


def build() -> dict:
    gov, od = load_sources()
    rolls_raw = gov + [r for r in od if (r.date, r.docket.lstrip("0")) not in
                       {(g.date, g.docket.lstrip("0")) for g in gov}]
    cleaned, people = clean.clean(rolls_raw)
    known = {p.split("-")[0] for p in people}
    od_by_key = {}
    if gov:
        od_clean, _ = clean.clean(od)
        for r in od_clean:
            od_by_key.setdefault((r.date, r.docket.lstrip("0")), []).append(r)

    rolls = []
    for r in sorted(cleaned, key=lambda x: (x.date, x.source_id), reverse=True):
        counts = Counter(v.vote for v in r.votes)
        problems = checks.check(r, known)
        twin = od_by_key.get((r.date, r.docket.lstrip("0")), []) if r.source == "bostongov" else []
        if len(twin) == 1:
            a = {(v.councillor, v.vote) for v in r.votes}
            b = {(v.councillor, v.vote) for v in twin[0].votes}
            if a != b:
                problems.append("The open dataset records this roll call differently: " + ", ".join(
                    f"{c} {v}" for c, v in sorted(b - a)) + ".")
        rolls.append({
            "id": r.id, "date": r.date, "docket": r.docket, "title": title(r.description, r.docket),
            "outcome": outcome(r.description), "description": r.description,
            "counts": {k: counts.get(k, 0) for k in KINDS},
            "election": any(v.vote == "choice" for v in r.votes),
            "split": counts.get("no", 0) > 0,
            "votes": [[v.councillor, v.vote, v.choice] if v.choice else [v.councillor, v.vote] for v in r.votes],
            "notes": r.notes, "problems": problems,
            "source": r.source,
            "source_url": (f"{ROLLCALL_URL}?search={r.docket}" if r.source == "bostongov" else DATASET_URL),
        })

    councillors = []
    for cid, p in people.items():
        mine = [(r, dict((v[0], v[1]) for v in r["votes"])) for r in rolls if any(v[0] == cid for v in r["votes"])]
        votes = Counter(m[cid] for _, m in mine)
        split = [(r, m) for r, m in mine if r["split"] and not r["election"]]
        against = sum(1 for r, m in split if m[cid] in ("yes", "no") and
                      m[cid] != ("yes" if r["counts"]["yes"] >= r["counts"]["no"] else "no"))
        agree = {}
        for other in people:
            if other == cid:
                continue
            both = [(m[cid], m[other]) for _, m in split if m.get(other) in ("yes", "no") and m[cid] in ("yes", "no")]
            if len(both) >= 5:
                agree[other] = {"n": len(both), "same": sum(a == b for a, b in both)}
        councillors.append({**p, "roll_calls": len(mine), "votes": {k: votes.get(k, 0) for k in KINDS},
                            "split_votes": len(split), "against_majority": against, "agreement": agree})
    councillors.sort(key=lambda c: (c["last"], c["name"]), reverse=True)

    stated = sum(1 for r in cleaned if checks.stated_tally(r.description))
    summary = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "roll_calls": len(rolls), "first": rolls[-1]["date"] if rolls else None, "latest": rolls[0]["date"] if rolls else None,
        "split": sum(r["split"] for r in rolls),
        "stated_tally": stated, "inconsistent": sum(bool(r["problems"]) for r in rolls),
        "notes": sum(len(r["notes"]) for r in rolls),
        "sources": [
            {"name": "boston.gov roll-call votes", "url": ROLLCALL_URL, "roll_calls": len(gov),
             "through": max((g.date for g in gov), default=None)},
            {"name": "Analyze Boston: City Council Roll Call Votes", "url": DATASET_URL, "roll_calls": len(od),
             "through": max((o.date for o in od), default=None), "licence": "Open Data Commons PDDL (public domain)"},
        ],
    }
    os.makedirs(OUT, exist_ok=True)
    for name, obj in [("rollcalls.json", rolls), ("councillors.json", councillors), ("summary.json", summary)]:
        with open(os.path.join(OUT, name), "w") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    return summary
