"""Check each roll call against itself: does the vote list match the tally the clerk wrote in the description?

A description usually ends with the outcome, e.g. "the order was passed: yeas 12 (Breadon, ...), nays 1
(Murphy)". When it states a count or names, the recorded votes should agree with them. A mismatch doesn't
say which side is wrong, so the site flags the record and shows both rather than picking one.
"""

from __future__ import annotations

import difflib
import re

from .clean import CleanRollCall, key

COUNT = {"yeas": "yes", "yea": "yes", "nays": "no", "nay": "no", "present": "present", "absent": "absent",
         "not present": "absent"}


def stated_tallies(description: str) -> list[dict[str, dict]]:
    """Every tally in the description, in order; each is {"yes": {"n": 12, "names": {...} or None}, ...}.
    A new tally starts at each "yeas": a description can hold a motion's vote, then the main question's."""
    tallies: list[dict[str, dict]] = []
    text = re.sub(r"\s+", " ", description)
    # "not present" before "present", so "not present 1" isn't read as a present vote
    pattern = r"\b(yeas?|nays?|not present|present|absent)\s+(\d{1,2})\b(?:\s*\(([^)]*)\))?"
    for m in re.finditer(pattern, text, flags=re.I):
        word, n, names = m.group(1).lower(), int(m.group(2)), m.group(3)
        vote = COUNT[word]
        if word.startswith("yea") or not tallies:
            tallies.append({})
        out = tallies[-1]
        keys = None
        if names:
            parts = re.split(r",|\band\b", names)
            parts = [re.sub(r"^\s*(councill?ors?|council president)\s+", "", p, flags=re.I) for p in parts]
            keys = {key(p) for p in parts if key(p)}
        if vote in out:  # "not present 1 (Flynn), absent 1 (Pepén)": two words for the same thing, so add them
            prev = out[vote]
            keys = (prev["names"] | keys) if prev["names"] is not None and keys is not None else None
            n += prev["n"]
        out[vote] = {"n": n, "names": keys}
    return tallies


def stated_tally(description: str) -> dict[str, dict]:
    """The last tally in the description, usually the final outcome."""
    t = stated_tallies(description)
    return t[-1] if t else {}


def closest(k: str, known: set[str]) -> str:
    """A description's spelling of a name, matched to a councillor one or two letters away ("Durkin")."""
    if k in known:
        return k
    m = difflib.get_close_matches(k, sorted(known), n=1, cutoff=0.8)
    return m[0] if m else k


WORD = {"yes": "voted yes", "no": "voted no", "present": "voted present", "absent": "were not present"}
ONE = {"yes": "voted yes", "no": "voted no", "present": "voted present", "absent": "was not present"}
AS = {"yes": "voting yes", "no": "voting no", "present": "voting present", "absent": "not present"}


def _names(keys, display) -> str:
    names = [display.get(k, k) for k in sorted(keys)]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _problems(stated, rc, display) -> list[str]:
    blank = {b.split("-")[0] for b in rc.blank}
    problems = []
    for vote, s in stated.items():
        recorded = [v.councillor.split("-")[0] for v in rc.votes if v.vote == vote]
        if vote == "absent" and blank:
            # a councillor listed with no vote at all is consistent with the clerk calling them absent
            named = s["names"] or set()
            recorded += sorted(blank & named) if named else sorted(blank)[: max(0, s["n"] - len(recorded))]
        if len(recorded) != s["n"]:
            problems.append(f"The description says {s['n']} {WORD[vote] if s['n'] != 1 else ONE[vote]}; "
                            f"the record lists {len(recorded) or 'none'}.")
        if s["names"] and s["names"] != set(recorded) and len(s["names"]) == s["n"]:
            gone, extra = s["names"] - set(recorded), set(recorded) - s["names"]
            if gone:
                problems.append(f"The description names {_names(gone, display)} as {AS[vote]}; the record doesn't.")
            if extra:
                problems.append(f"The record lists {_names(extra, display)} as {AS[vote]}; the description doesn't.")
    return problems


def check(rc: CleanRollCall, known: set[str] | None = None, display: dict[str, str] | None = None) -> list[str]:
    """Problems found in one roll call, as sentences; empty when it is consistent or states nothing.

    The record is consistent if it matches any tally its description states (a description can carry a
    motion's vote and then the main question's). Otherwise the problems are reported against the last
    tally, usually the final outcome. `known` is every councillor's name key, used to read misspelled
    names in the description; `display` maps a key to the name shown on the site."""
    display = display or {}
    tallies = stated_tallies(rc.description)
    if not tallies or any(v.vote == "choice" for v in rc.votes):
        return []
    if known:
        for t in tallies:
            for s in t.values():
                if s["names"]:
                    s["names"] = {closest(k, known) for k in s["names"]}
    results = [_problems(t, rc, display) for t in tallies]
    return [] if any(not r for r in results) else results[-1]
