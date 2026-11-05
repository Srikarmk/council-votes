import { fmt, longDate, rollcalls, summary } from "@/lib/data"

export const metadata = { title: "About the data" }

export default function About() {
  const notes = rollcalls.reduce((n, r) => n + r.notes.length, 0)
  const noted = rollcalls.filter((r) => r.notes.length).length
  return (
    <>
      <div className="title-row">
        <div>
          <h1>About the data</h1>
          <p className="lede">
            Where every vote on this site comes from, what was changed to read it, and how the records are checked.
            Last built {longDate(summary.generated.slice(0, 10))}.
          </p>
        </div>
      </div>

      <div className="grid">
        <section className="card span-7">
          <div className="card-head"><h2>Sources</h2></div>
          <div className="card-body">
            <table>
              <thead><tr><th>Source</th><th className="r">Roll calls</th><th className="r">Through</th></tr></thead>
              <tbody>
                {summary.sources.map((s) => (
                  <tr key={s.url}>
                    <td><a href={s.url} rel="noopener">{s.name}</a>{s.licence ? <span className="muted small"><br />{s.licence}</span> : null}</td>
                    <td className="r">{s.roll_calls ? fmt(s.roll_calls) : <span className="dash">0</span>}</td>
                    <td className="r">{s.through ? longDate(s.through) : <span className="dash">–</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ marginTop: 16 }}>
              Both are published by the City of Boston. The roll-call pages on boston.gov are the main source; the open
              dataset, which the City placed in the public domain, covers 2008 to March 2024 and is used where the pages
              aren&apos;t available and as a cross-check where both have a roll call. The site is rebuilt from them on a schedule.
            </p>
            <p style={{ marginTop: 12 }}>
              This is an independent project. It is not affiliated with or endorsed by the City of Boston, and for any
              official purpose the City&apos;s own records are the reference. Meeting video is on the City Council&apos;s
              channels; this site links to records and doesn&apos;t copy video.
            </p>
          </div>
        </section>

        <section className="card span-5">
          <div className="card-head"><h2>What a roll call is</h2></div>
          <div className="card-body">
            <p>
              A roll call is a vote in which each councillor&apos;s vote is recorded by name. Many Council decisions are
              made by voice vote or without objection and have no roll call, so they aren&apos;t here. A councillor can
              vote yes or no, vote present, abstain, or not be present.
            </p>
          </div>
        </section>

        <section className="card span-6">
          <div className="card-head"><h2>What was changed to read the records</h2></div>
          <div className="card-body">
            <p>
              The records name councillors by surname and use short codes for votes. To join them up, {fmt(notes)} small
              changes were made across {fmt(noted)} roll calls, and each one is listed on the roll call&apos;s own page:
            </p>
            <ul>
              <li>misspelled surnames read as the councillor they plainly refer to (&ldquo;Luoijeune&rdquo;, &ldquo;Webber&rdquo;);</li>
              <li>a vacant seat recorded as a vote, dropped;</li>
              <li>a name field holding a stray letter, read as a councillor only when exactly one councillor who voted elsewhere that day is missing from the roll call, and otherwise left unidentified;</li>
              <li>a surname that disappears for more than a year and comes back, listed as two stretches, because it may be two different councillors.</li>
            </ul>
            <p>No vote is changed, added or removed beyond these.</p>
          </div>
        </section>

        <section className="card span-6">
          <div className="card-head"><h2>How the records are checked</h2></div>
          <div className="card-body">
            <p>
              Most records end with the clerk&apos;s tally, such as &ldquo;yeas 12, nays 1 (Murphy)&rdquo;. Each record&apos;s
              listed votes are compared with its own stated tally: the counts, and the names where the tally names them.
              Of {fmt(summary.stated_tally)} records that state a tally, {fmt(summary.inconsistent)} don&apos;t match.
              They&apos;re marked on the site and gathered under Contradictions, with both versions shown.
            </p>
          </div>
        </section>
      </div>
    </>
  )
}
