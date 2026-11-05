import os

from councilvotes import checks, clean, parse
from councilvotes.sources import last_page

HERE = os.path.dirname(__file__)
PAGE = os.path.join(HERE, "fixtures", "rollcall-page-0-2026-03-09.html")


def row(i, rid, date, who, vote, docket="0001", subject="An order; yeas 2."):
    return {"_id": i, "roll_call_id": rid, "docket_number": docket, "subject": subject, "vote_date": date,
            "councillor": who, "vote": vote}


def test_parses_a_real_boston_gov_page():
    html = open(PAGE).read()
    rolls = parse.parse_rollcall_page(html)
    assert len(rolls) == 10 and last_page(html) == 151
    first = rolls[0]
    assert (first.source_id, first.docket, first.date) == ("16568081", "0424", "2026-03-04")
    assert len(first.votes) == 13 and first.votes[0] == ("Breadon", "Yes")
    assert first.description.startswith("Councilor Breadon called Docket #0424")
    assert {v for r in rolls for _, v in r.votes} == {"Yes", "Present", "Not Present"}


def test_names_typos_vacancies_and_a_shared_surname():
    rows, i = [], 0
    # Murphy votes through 2008, disappears for years, and a Murphy returns in 2022; Flynn only in 2022
    for rid, date, extra in [("1", "2008-01-07", []), ("2", "2008-06-01", []), ("3", "2008-12-01", []),
                             ("4", "2022-02-02", [("Vacant", "NP")]), ("5", "2022-03-02", [("Luoijeune", "Y")]),
                             ("6", "2022-04-06", [("W", "Y")])]:
        people = [("Murphy", "Y")] + ([("Flynn", "N")] if rid > "3" else []) \
            + ([("Louijeune", "Y")] if rid in ("4", "6") else []) + extra
        for who, v in people:
            i += 1
            rows.append(row(i, rid, date, who, v))
    rolls, people = clean.clean(parse.parse_opendata(rows))
    by = {r.source_id: r for r in rolls}
    assert {v.councillor for v in by["1"].votes} == {"murphy"}
    assert {v.councillor for v in by["4"].votes} == {"murphy-2", "flynn", "louijeune"}
    assert people["murphy"]["shares_name"] and people["murphy-2"]["first"] == "2022-02-02"
    assert any("vacant" in n for n in by["4"].notes) and len(by["4"].votes) == 3
    assert any("misspelled name 'Luoijeune'" in n for n in by["5"].notes)
    # "W" is a slip; Louijeune voted elsewhere that day? No: only on 04-06, where she is already present,
    # so the slip can't be pinned on anyone and stays unidentified
    assert any(v.councillor == "unidentified" for v in by["6"].votes)


def test_a_slip_is_resolved_only_when_one_councillor_is_missing():
    rows = [row(1, "1", "2023-07-19", "Worrell", "Y"), row(2, "1", "2023-07-19", "Flynn", "Y"),
            row(3, "2", "2023-07-19", "Flynn", "Y"), row(4, "2", "2023-07-19", "Wt6", "Y"),
            row(5, "3", "2023-08-01", "Worrell", "Y"), row(6, "3", "2023-08-01", "Flynn", "Y"),
            row(7, "4", "2023-09-01", "Worrell", "Y"), row(8, "4", "2023-09-01", "Flynn", "Y")]
    rolls, _ = clean.clean(parse.parse_opendata(rows))
    two = next(r for r in rolls if r.source_id == "2")
    assert {v.councillor for v in two.votes} == {"flynn", "worrell"}
    assert any("only councillor who voted elsewhere that day" in n for n in two.notes)


def test_an_election_keeps_the_candidate():
    rows = [row(1, "1", "2009-01-05", "Ross", "Ross"), row(2, "1", "2009-01-05", "Tobin", "Feeney"),
            row(3, "1", "2009-01-05", "Feeney", "Feeney")]
    for i, rid in enumerate(["2", "3"]):
        rows += [row(10 + 3 * i + j, rid, f"2009-0{i + 2}-01", w, "Y") for j, w in enumerate(["Ross", "Tobin", "Feeney"])]
    rolls, _ = clean.clean(parse.parse_opendata(rows))
    votes = {v.councillor: (v.vote, v.choice) for v in rolls[0].votes}
    assert votes == {"ross": ("choice", "ross"), "tobin": ("choice", "feeney"), "feeney": ("choice", "feeney")}


def test_stated_tally_reads_the_final_vote_and_not_present():
    d = ("Motion did not prevail; yeas 5, nays 8 (A, B, C, D, E, F, G, H). On motion of Councilor Coletta, "
         "the ordinance was passed; yeas 8, nays 3 (FitzGerald, Flynn, Murphy), present 2 (Fernandes Anderson, "
         "Mejia), not present 1 (Councilor Worrell).")
    t = checks.stated_tally(d)
    assert t["yes"]["n"] == 8 and t["no"]["names"] == {"fitzgerald", "flynn", "murphy"}
    assert t["present"]["names"] == {"fernandesanderson", "mejia"} and t["absent"]["names"] == {"worrell"}


def test_check_flags_a_record_that_contradicts_its_description():
    rc = clean.CleanRollCall("x", "opendata", "3207", "0001", "2023-11-29",
                             "the order failed on passage; yeas 5, nays 2 (Durkin, Louijeune)",
                             [clean.Vote(n, "yes") for n in ["a", "b", "c", "d", "e", "durkan", "louijeune"]])
    problems = checks.check(rc, {"durkan", "louijeune", "a", "b", "c", "d", "e"}, {"durkan": "Durkan", "louijeune": "Louijeune"})
    assert problems[0] == "The description says 5 voted yes; the record lists 7."
    assert problems[1] == "The description says 2 voted no; the record lists none."
    # "Durkin" in the description is read as Durkan, so the complaint is about the votes, not the typo
    assert problems[2] == "The description names Durkan and Louijeune as voting no; the record doesn't."
    ok = clean.CleanRollCall("y", "opendata", "1", "0001", "2023-11-29", "passed; yeas 2 (Durkan, Louijeune)",
                             [clean.Vote("durkan", "yes"), clean.Vote("louijeune", "yes")])
    assert checks.check(ok, {"durkan", "louijeune"}) == []
