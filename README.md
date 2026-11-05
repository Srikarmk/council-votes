# Yeas & Nays

Every recorded roll-call vote of the Boston City Council since 2008, as a site you can search: how each
councillor voted, which votes split the Council, who votes with whom, and the records where the City's own
data contradicts itself.

An independent project, not affiliated with or endorsed by the City of Boston.

## Where the votes come from

| Source | What it has | Licence |
|---|---|---|
| [boston.gov roll-call votes](https://www.boston.gov/departments/city-council/city-council-roll-call-votes) | 1,821 roll calls, January 2008 to now, with each councillor's vote and a one-line summary of each docket | City of Boston terms of use, which allow republishing City information without implying endorsement |
| [Analyze Boston: City Council Roll Call Votes](https://data.boston.gov/dataset/city-council-roll-call-votes) | 1,235 roll calls, January 2008 to March 2024, one row per councillor's vote | Open Data Commons PDDL (public domain) |

boston.gov is the main source. The dataset is a cross-check: of the 1,179 roll calls both cover, they agree
vote for vote on 1,158, and the dataset repeats 40 roll calls that boston.gov has once. Raw responses are kept in `data/raw/`, so every number on the site can be traced
to what the City published. Pages are fetched three seconds apart with an identifying user agent, and the
daily run fetches only the newest three pages. Meeting video is not copied; YouTube's terms don't allow it.

## What is changed, and what is checked

The records name councillors by surname and use short codes for votes. To join them up, `clean.py` reads
misspelled surnames as the councillor they refer to, drops vacant seats, keeps a council president election's
votes as choices, and resolves a stray letter in a name field only when exactly one councillor who voted
elsewhere that day is missing. A surname that vanishes for over a year and returns is listed as two stretches,
because the data can't tell a returning councillor from a new one with the same name. Every change is written
on the roll call's own page.

`checks.py` compares each record's votes with the tally the clerk wrote in its description ("yeas 10, nays 2
(Flynn, Murphy)"); a record counts as consistent if it matches any tally its description states. Of the 1,530
records that state one, 84 don't match it: unanimous records whose description names the no votes, a council
of 13 with 26 recorded votes, a "present" where the clerk wrote "not present". They are flagged on the site with
both versions shown; neither is changed. A councillor listed with no vote at all is left out of the counts and
treated as consistent with the clerk calling them absent.

## Run it

Requires [uv](https://docs.astral.sh/uv/) and pnpm.

```sh
uv sync
uv run councilvotes dataset        # the Analyze Boston dataset
uv run councilvotes fetch --all    # every boston.gov page, about 150, three seconds apart
uv run councilvotes build          # web/data/*.json and web/public/index.json
uv run pytest

cd web && pnpm install && pnpm dev # http://localhost:3000
pnpm build                         # a static site in web/out
```

`.github/workflows/update.yml` runs `councilvotes update` every morning: the newest boston.gov pages, the
dataset, a rebuild and the tests, then a commit if anything changed. If boston.gov hasn't answered for a week,
the run fails so the failure email goes out.

## Layout

```
src/councilvotes/  sources (fetching), parse, clean (logged name and vote fixes), checks (self-consistency),
                   build (site JSON), cli
tests/             parser on a real boston.gov page, cleaning rules, the tally check
data/raw/          what the City published, as fetched
web/               the Next.js site, built statically from web/data
```

## License

MIT for the code. The vote records are the City of Boston's.
