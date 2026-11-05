import Link from "next/link"
import { StripLegend, VoteRow } from "@/components/strip"
import { councillors, currentCouncil, fmt, longDate, meetings, pct, rollcalls, summary } from "@/lib/data"

export default function Home() {
  const [latest] = meetings()
  const split = rollcalls.filter((r) => r.split && !r.election)
  const flagged = rollcalls.filter((r) => r.problems.length)
  const council = currentCouncil()
  const latestSplit = latest.rolls.filter((r) => r.split).length
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Boston City Council votes</h1>
          <p className="lede">
            How each councillor voted on every recorded roll call since {summary.first.slice(0, 4)}.
            The latest meeting, on <strong>{longDate(latest.date)}</strong>, held {latest.rolls.length} roll calls
            {latestSplit ? <>, and <strong>{latestSplit} split the Council</strong></> : ", none of them split"}.
          </p>
        </div>
        <form className="search" action="/votes/" role="search">
          <input id="q" name="q" type="search" aria-label="Search votes" placeholder="Search by topic, docket or councillor" />
          <button className="btn" type="submit">Search</button>
        </form>
      </div>

      <div className="stack">
        <section className="card figures" aria-label="The record in numbers">
          <div className="figure">
            <span className="kpi">{fmt(summary.roll_calls)}</span>
            <span className="label">roll calls recorded, {summary.first.slice(0, 4)} to {summary.latest.slice(0, 4)}</span>
          </div>
          <div className="figure">
            <span className="kpi hue">{fmt(split.length)}</span>
            <span className="label">split, with at least one councillor voting no ({pct(split.length, summary.roll_calls)})</span>
          </div>
          <div className="figure">
            <span className="kpi">{fmt(councillors.length)}</span>
            <span className="label">councillors over those years, each with a full voting record</span>
          </div>
          <div className="figure">
            <span className="kpi warn">{fmt(flagged.length)}</span>
            <span className="label">records whose votes contradict their own written tally</span>
          </div>
        </section>

        <div className="grid">
          <section className="card span-7">
            <div className="card-head">
              <h2>Latest meeting: {longDate(latest.date)}</h2>
              <span className="meta">{latest.rolls.length} roll calls</span>
            </div>
            <div className="card-body">
              <ul className="rows">
                {latest.rolls.slice(0, 7).map((r) => <li key={r.id}><VoteRow rc={r} showDate={false} /></li>)}
              </ul>
            </div>
            <div className="card-foot"><StripLegend /></div>
          </section>

          <div className="span-5 stack">
            <section className="card">
              <div className="card-head">
                <h2>The Council in the latest meeting</h2>
                <Link className="meta" href="/councillors/">All {councillors.length}</Link>
              </div>
              <div className="card-body">
                <table>
                  <thead><tr><th>Councillor</th><th className="r">Roll calls</th><th className="r">Voted no</th><th className="r">Not present</th></tr></thead>
                  <tbody>
                    {council.map((c) => (
                      <tr key={c.id}>
                        <td><Link href={`/councillors/${c.id}/`}>{c.name}</Link></td>
                        <td className="r">{fmt(c.roll_calls)}</td>
                        <td className="r">{c.votes.no ? <span className="no-ink">{fmt(c.votes.no)}</span> : <span className="dash">0</span>}</td>
                        <td className="r">{c.votes.absent ? fmt(c.votes.absent) : <span className="dash">0</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="card">
              <div className="card-head">
                <h2>Records that contradict themselves</h2>
                <Link className="meta" href="/contradictions/">All {flagged.length}</Link>
              </div>
              <div className="card-body">
                <p className="muted small" style={{ marginBottom: 4 }}>
                  The clerk&apos;s description states a tally that the recorded votes don&apos;t match. Both are shown.
                </p>
                <ul className="rows">
                  {flagged.slice(0, 3).map((r) => <li key={r.id}><VoteRow rc={r} /></li>)}
                </ul>
              </div>
            </section>
          </div>

          <section className="card span-12">
            <div className="card-head">
              <h2>Recent split votes</h2>
              <Link className="meta" href="/votes/?split=1">All {fmt(split.length)}</Link>
            </div>
            <div className="card-body">
              <ul className="rows">
                {split.slice(0, 6).map((r) => <li key={r.id}><VoteRow rc={r} /></li>)}
              </ul>
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
