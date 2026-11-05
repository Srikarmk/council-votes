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


def stated_tally(description: str) -> dict[str, dict]:
    """Counts and names stated in the description, by vote: {"yes": {"n": 12, "names": {...} or None}}."""
    out: dict[str, dict] = {}
    text = re.sub(r"\s+", " ", description)
    # "not present" before "present", so "not present 1" isn't read as a present vote
    pattern = r"\b(yeas?|nays?|not present|present|absent)\s+(\d{1,2})\b(?:\s*\(([^)]*)\))?"
    for m in re.finditer(pattern, text, flags=re.I):
        word, n, names = m.group(1).lower(), int(m.group(2)), m.group(3)
        vote = COUNT[word]
        if word.startswith("yea"):  # a new tally starts: a motion, then the main question; keep the last
            out = {}
        keys = None
        if names:
            parts = re.split(r",|\band\b", names)
            parts = [re.sub(r"^\s*(councill?ors?|council president)\s+", "", p, flags=re.I) for p in parts]
            keys = {key(p) for p in parts if key(p)}
        out[vote] = {"n": n, "names": keys}
    return out


def closest(k: str, known: set[str]) -> str:
    """A description's spelling of a name, matched to a councillor one or two letters away ("Durkin")."""
    if k in known:
        return k
    m = difflib.get_close_matches(k, sorted(known), n=1, cutoff=0.8)
    return m[0] if m else k


def check(rc: CleanRollCall, known: set[str] | None = None) -> list[str]:
    """Problems found in one roll call, as sentences; empty when it is consistent or states nothing.
    `known` is every councillor's name key, used to read misspelled names in the description."""
    stated = stated_tally(rc.description)
    if known:
        for s in stated.values():
            if s["names"]:
                s["names"] = {closest(k, known) for k in s["names"]}
    if not stated or any(v.vote == "choice" for v in rc.votes):
        return []
    problems = []
    for vote, s in stated.items():
        recorded = [v.councillor.split("-")[0] for v in rc.votes if v.vote == vote]
        if len(recorded) != s["n"]:
            problems.append(f"The description says {s['n']} {vote}, but the record lists {len(recorded)}.")
        if s["names"] and s["names"] != set(recorded) and len(s["names"]) == s["n"]:
            extra = sorted(set(recorded) - s["names"])
            gone = sorted(s["names"] - set(recorded))
            bits = []
            if gone:
                bits.append("named in the description but not recorded as " + vote + ": " + ", ".join(gone))
            if extra:
                bits.append("recorded as " + vote + " but not named: " + ", ".join(extra))
            problems.append("Names differ (" + "; ".join(bits) + ").")
    return problems
