"""Turn published names and vote codes into one vocabulary, and log every change.

Nothing is fixed silently. Each roll call carries notes saying what was changed and why, and the site
shows them next to the record.

Names: the sources give surnames, with typos ("Luoijeune", "Webber") and one name change ("Coletta",
later "Coletta Zapata"). Two councillors have shared a surname ("Murphy"); they are told apart by a gap of
more than a year in that surname's votes, which comes from the data, not from outside knowledge.
"Vacant" marks an empty seat and is dropped. A name seen in fewer than three roll calls ("W", "b") is a
data-entry slip; it is resolved only when exactly one councillor who voted elsewhere that day is missing
from the roll call, and otherwise kept as unidentified.

Votes: yes, no, present, abstain and absent. A council president election records the candidate's name
instead, which is kept as a choice.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from .parse import RollCall

VOTE_CODES = {
    "y": "yes", "yes": "yes", "yea": "yes",
    "n": "no", "no": "no", "nay": "no",
    "np": "absent", "not present": "absent", "absent": "absent",
    "p": "present", "present": "present",
    "abstain": "abstain", "abstained": "abstain",
}
VACANT = {"vacant", "vancant"}
TYPOS = {"luoijeune": "louijeune", "colletta": "coletta", "worreell": "worrell", "webber": "weber",
         "frnandesanderson": "fernandesanderson"}
RENAMED = {"colettazapata": "coletta"}  # same councillor; shown under the newer name
SPLIT_GAP_DAYS = 366
MIN_ROLL_CALLS = 3


def raw_key(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z]", "", s)


def key(name: str) -> str:
    s = raw_key(name)
    return TYPOS.get(s) or RENAMED.get(s) or s


@dataclass
class Vote:
    councillor: str        # canonical id; "murphy-2" for the second councillor named Murphy
    vote: str              # yes, no, present, abstain, absent, choice, unknown
    choice: str = ""       # in an election, the candidate's id
    published: tuple[str, str] = ("", "")


@dataclass
class CleanRollCall:
    id: str
    source: str
    source_id: str
    docket: str
    date: str
    description: str
    votes: list[Vote]
    notes: list[str] = field(default_factory=list)


def display_names(rolls: list[RollCall]) -> dict[str, str]:
    """Each name key's spelling on its latest date, ignoring typos; accents win a tie ("Pepén")."""
    best: dict[str, tuple[str, int, str]] = {}
    for r in rolls:
        for name, _ in r.votes:
            rk, k = raw_key(name), key(name)
            if not k or k in VACANT or rk in TYPOS:
                continue
            score = (r.date, any(ord(c) > 127 for c in name))
            if k not in best or score > best[k][:2]:
                best[k] = (*score, name)
    return {k: v[2] for k, v in best.items()}


def terms(rolls: list[RollCall]) -> dict[str, list[tuple[str, str]]]:
    """Per name key, the spans of dates it votes in, split wherever it is absent for over a year."""
    dates: dict[str, set[str]] = {}
    calls: dict[str, int] = {}
    for r in rolls:
        for k in {key(n) for n, _ in r.votes}:
            if k and k not in VACANT:
                dates.setdefault(k, set()).add(r.date)
                calls[k] = calls.get(k, 0) + 1
    out = {}
    for k, ds in dates.items():
        if calls[k] < MIN_ROLL_CALLS:
            continue
        ds = sorted(ds)
        spans, start, prev = [], ds[0], ds[0]
        for d in ds[1:]:
            if (date.fromisoformat(d) - date.fromisoformat(prev)).days > SPLIT_GAP_DAYS:
                spans.append((start, prev))
                start = d
            prev = d
        spans.append((start, prev))
        out[k] = spans
    return out


def councillor_id(k: str, day: str, spans: dict[str, list[tuple[str, str]]]) -> str:
    sp = spans.get(k, [])
    for i, (a, b) in enumerate(sp):
        if a <= day <= b:
            return k if i == 0 else f"{k}-{i + 1}"
    return k


def clean(rolls: list[RollCall]) -> tuple[list[CleanRollCall], dict[str, dict]]:
    spans = terms(rolls)
    names = display_names(rolls)
    known = set(spans)
    by_date: dict[str, set[str]] = {}
    for r in rolls:
        by_date.setdefault(r.date, set()).update(key(n) for n, _ in r.votes)

    out = []
    for r in rolls:
        notes, votes = [], []
        here = {key(n) for n, _ in r.votes}
        for name, raw in r.votes:
            k = key(name)
            code = VOTE_CODES.get(raw.strip().casefold())
            if k in VACANT:
                notes.append(f"Dropped a vacant seat recorded as {raw!r}.")
                continue
            if k not in known:
                missing = sorted(x for x in by_date.get(r.date, set()) - here if x in known)
                if len(missing) == 1:
                    k = missing[0]
                    here.add(k)
                    notes.append(f"Read the name {name!r} as {names[k]}: the only councillor who voted "
                                 f"elsewhere that day and is missing here.")
                else:
                    notes.append(f"Could not identify the councillor recorded as {name!r}.")
                    votes.append(Vote("unidentified", code or "unknown", published=(name, raw)))
                    continue
            elif raw_key(name) in TYPOS:
                notes.append(f"Read the misspelled name {name!r} as {names[k]}.")
            cid = councillor_id(k, r.date, spans)
            if code:
                votes.append(Vote(cid, code, published=(name, raw)))
            elif key(raw) in known:
                votes.append(Vote(cid, "choice", councillor_id(key(raw), r.date, spans), published=(name, raw)))
            else:
                notes.append(f"Unrecognised vote {raw!r} for {names[k]}.")
                votes.append(Vote(cid, "unknown", published=(name, raw)))
        ids = [v.councillor for v in votes if v.councillor != "unidentified"]
        for d in sorted({c for c in ids if ids.count(c) > 1}):
            notes.append(f"{names[d.split('-')[0]]} appears more than once in this roll call.")
        out.append(CleanRollCall(f"{r.source}-{r.source_id}", r.source, r.source_id, r.docket, r.date,
                                 r.description, votes, notes))

    people = {}
    for k, sp in spans.items():
        for i, (a, b) in enumerate(sp):
            cid = k if i == 0 else f"{k}-{i + 1}"
            people[cid] = {"id": cid, "name": names.get(k, k), "first": a, "last": b, "shares_name": len(sp) > 1}
    return out, people
