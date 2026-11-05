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
VOTE_LETTER = {"yes": "y", "no": "n", "present": "p", "abstain": "a", "absent": "x", "choice": "c", "unknown": "u"}


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
    first = re.split(r"(?<=[a-z0-9)\"”])\.\s+(?=[A-Z])|(?<=\.[\"”])\s+(?=[A-Z])", t, maxsplit=1)[0]
    first = first[0].upper() + first[1:] if first else first
    return first if len(first) <= 180 else first[:177].rsplit(" ", 1)[0] + "…"


def outcome(description: str) -> str:
    """The clerk's closing sentence, which states what happened and the tally."""
    t = re.sub(r"\s+", " ", description).strip()
    parts = re.split(r"(?<=[.;])\s+", t)
    with_tally = [p for p in parts if re.search(r"\byeas?\b", p, flags=re.I)]
    return (with_tally[-1] if with_tally else parts[-1]).strip()


ROSTER_SIDE_DAYS = 90
ROSTER_SHARE = 0.5  # a sitting councillor is listed (absent or not) in nearly every roll call
ROSTER_MIN_SIDE = 3


def roster_outliers(rolls: list[clean.CleanRollCall]) -> dict[str, list[str]]:
    """Councillors listed in a roll call who are rare on both sides of it: in fewer than a quarter of the
    roll calls in the three months before and in the three months after. That's the mark of a record that
    reuses an older council's roster (seen in 2021-23, listing councillors who had left). A councillor's
    real first or last vote is common on one side, so it isn't caught. Keyed by roll call id."""
    import bisect
    from datetime import date
    order = sorted(rolls, key=lambda r: r.date)
    days = [date.fromisoformat(r.date).toordinal() for r in order]
    sets = [{v.councillor for v in r.votes} for r in order]
    out: dict[str, list[str]] = {}
    for i, r in enumerate(order):
        before = [j for j in range(bisect.bisect_left(days, days[i] - ROSTER_SIDE_DAYS), i) if days[j] < days[i]]
        after = [j for j in range(i + 1, bisect.bisect_right(days, days[i] + ROSTER_SIDE_DAYS)) if days[j] > days[i]]
        if len(before) < ROSTER_MIN_SIDE or len(after) < ROSTER_MIN_SIDE:
            continue
        rare = lambda c, side: sum(c in sets[j] for j in side) / len(side) < ROSTER_SHARE  # noqa: E731
        odd = sorted(c for c in sets[i] if c != "unidentified" and rare(c, before) and rare(c, after))
        if odd:
            out[r.id] = odd
    return out


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

    roster = roster_outliers(cleaned)
    rolls = []
    for r in sorted(cleaned, key=lambda x: (x.date, x.source_id), reverse=True):
        counts = Counter(v.vote for v in r.votes)
        problems = checks.check(r, known, {p.split("-")[0]: v["name"] for p, v in people.items()})
        # Where the open dataset has the same roll call (same date and docket; the closest description when
        # it has several), say how its votes differ. That's a difference between two publications, kept apart
        # from a record that contradicts itself.
        differs = []
        twins = od_by_key.get((r.date, r.docket.lstrip("0")), []) if r.source == "bostongov" else []
        if twins:
            words = set(re.findall(r"\w+", r.description.lower()))
            twin = max(twins, key=lambda t: len(words & set(re.findall(r"\w+", t.description.lower()))))
            mine = {v.councillor: v.vote for v in r.votes}
            theirs = {v.councillor: v.vote for v in twin.votes}
            for c in sorted(set(mine) | set(theirs)):
                if c != "unidentified" and mine.get(c) != theirs.get(c):
                    nm = people.get(c, {}).get("name", c)
                    w = lambda v: {"absent": "not present", None: "not listed"}.get(v, v)  # noqa: E731
                    differs.append(f"{nm}: {w(theirs.get(c))} in the dataset, {w(mine.get(c))} on boston.gov.")
        rolls.append({
            "id": r.id, "date": r.date, "docket": r.docket,
            # the City's own one-line summary where boston.gov shows one, else the description's first sentence
            "title": r.summary or title(r.description, r.docket), "title_source": "city" if r.summary else "description",
            "outcome": outcome(r.description), "description": r.description,
            "counts": {k: counts.get(k, 0) for k in KINDS},
            "election": any(v.vote == "choice" for v in r.votes),
            "split": counts.get("no", 0) > 0,
            "votes": [[v.councillor, v.vote, v.choice] if v.choice else [v.councillor, v.vote] for v in r.votes],
            "notes": r.notes, "problems": problems, "dataset_differs": differs, "roster": roster.get(r.id, []),
            "source": r.source,
            "source_url": (f"{ROLLCALL_URL}?search={r.docket}" if r.source == "bostongov" else DATASET_URL),
        })

    councillors = []
    for cid, p in people.items():
        # a councillor's record leaves out the roll calls where they're listed on an older roster
        mine = [(r, dict((v[0], v[1]) for v in r["votes"] if v[0] not in r["roster"])) for r in rolls
                if any(v[0] == cid for v in r["votes"]) and cid not in r["roster"]]
        if mine:
            p = {**p, "first": min(r["date"] for r, _ in mine), "last": max(r["date"] for r, _ in mine)}
        votes = Counter(m[cid] for _, m in mine)
        split = [(r, m) for r, m in mine if r["split"] and not r["election"]]
        against = sum(1 for r, m in split if m[cid] in ("yes", "no") and
                      m[cid] != ("yes" if r["counts"]["yes"] >= r["counts"]["no"] else "no"))
        agree = {}
        for other in sorted(people):  # sorted, so an unchanged record writes an unchanged file
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
        "compared_with_dataset": sum(1 for r in rolls if r["source"] == "bostongov" and r["date"] <= max((o.date for o in od), default="")),
        "dataset_differs": sum(bool(r["dataset_differs"]) for r in rolls),
        "roster_outliers": sum(bool(r["roster"]) for r in rolls),
        "dataset_duplicates": len(od) - len({(o.date, o.docket.lstrip("0"), o.description.strip()) for o in od}),
        "sources": [
            {"name": "boston.gov roll-call votes", "url": ROLLCALL_URL, "roll_calls": len(gov),
             "through": max((g.date for g in gov), default=None)},
            {"name": "Analyze Boston: City Council Roll Call Votes", "url": DATASET_URL, "roll_calls": len(od),
             "through": max((o.date for o in od), default=None), "licence": "Open Data Commons PDDL (public domain)"},
        ],
    }
    os.makedirs(OUT, exist_ok=True)
    dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    # "generated" is when the data last changed: a rebuild that changes nothing keeps the old time, so the
    # scheduled job commits (and the site redeploys) only when there is something new.
    try:
        before = {n: open(os.path.join(OUT, n)).read() for n in ("rollcalls.json", "councillors.json", "summary.json")}
        old = json.loads(before["summary.json"])
        if (before["rollcalls.json"] == dump(rolls) and before["councillors.json"] == dump(councillors)
                and {**old, "generated": None} == {**summary, "generated": None}):
            summary["generated"] = old["generated"]
    except (OSError, ValueError, KeyError):
        pass
    for name, obj in [("rollcalls.json", rolls), ("councillors.json", councillors), ("summary.json", summary)]:
        with open(os.path.join(OUT, name), "w") as f:
            f.write(dump(obj))
    # A compact index the browser loads for search and filters: no full descriptions, no notes.
    index = [{"id": r["id"], "d": r["date"], "k": r["docket"], "t": r["title"], "c": r["counts"],
              "s": int(r["split"]), "p": 1 if r["problems"] else 2 if r["roster"] else 0, "e": int(r["election"]),
              "v": "".join(VOTE_LETTER[v[1]] for v in r["votes"]), "w": [v[0] for v in r["votes"]],
              "x": re.sub(r"\s+", " ", r["description"])}  # searched, never shown
             for r in rolls]
    os.makedirs(os.path.join(ROOT, "web", "public"), exist_ok=True)
    with open(os.path.join(ROOT, "web", "public", "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    return summary
