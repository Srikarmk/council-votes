import Link from "next/link"
import { fmt, listNames, rollcalls, shortDate, summary, type RollCall } from "@/lib/data"
import { Strip } from "@/components/strip"

export const metadata = { title: "Contradictions" }

function Rows({ rows, reason }: { rows: RollCall[]; reason: (r: RollCall) => string }) {
  return (
    <ul className="rows">
      {rows.map((r) => (
        <li key={r.id}>
          <Link href={`/votes/${r.id}/`} className="vote-row" style={{ alignItems: "start" }}>
            <Strip rc={r} />
            <span>
              <span className="vote-title">{r.title}</span>
              <span className="vote-sub">{shortDate(r.date)} · Docket {r.docket}</span>
              <span className="vote-sub" style={{ color: "var(--warn)" }}>{reason(r)}</span>
            </span>
            <span className="tally"><b>{r.counts.yes}</b> yes · <span className={r.counts.no ? "no" : ""}>{r.counts.no}</span> no</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default function Contradictions() {
  const tally = rollcalls.filter((r) => r.problems.length)
  const roster = rollcalls.filter((r) => r.roster.length)
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Records that contradict themselves</h1>
          <p className="lede">
            Most of the City&apos;s roll-call records end with the clerk&apos;s tally, such as &ldquo;yeas 10, nays 2 (Flynn,
            Murphy)&rdquo;. Of the <strong>{fmt(summary.stated_tally)}</strong> that state one, <strong>{fmt(tally.length)}</strong> list
            votes that don&apos;t match it. Separately, {fmt(roster.length)} list councillors from an earlier Council. The records
            don&apos;t say which version is right, so both are shown, unchanged.
          </p>
        </div>
      </div>
      <div className="stack">
        <section className="card">
          <div className="card-head"><h2>Votes that don&apos;t match the written tally</h2><span className="meta">{fmt(tally.length)}</span></div>
          <div className="card-body"><Rows rows={tally} reason={(r) => r.problems.join(" ")} /></div>
        </section>
        <section className="card">
          <div className="card-head"><h2>Records that list an earlier Council</h2><span className="meta">{fmt(roster.length)}</span></div>
          <div className="card-body">
            <p className="muted small" style={{ marginBottom: 4 }}>
              Each lists councillors who appear in fewer than half of the roll calls in the three months before and after it.
              Their votes in these records are left out of their voting records on this site.
            </p>
            <Rows rows={roster} reason={(r) => `Lists ${listNames(r.roster)}.`} />
          </div>
        </section>
      </div>
    </>
  )
}
