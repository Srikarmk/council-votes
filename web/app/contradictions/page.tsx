import Link from "next/link"
import { fmt, rollcalls, shortDate, summary } from "@/lib/data"
import { Strip } from "@/components/strip"

export const metadata = { title: "Contradictions" }

export default function Contradictions() {
  const flagged = rollcalls.filter((r) => r.problems.length)
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Records that contradict themselves</h1>
          <p className="lede">
            Most of the City&apos;s roll-call records end with the clerk&apos;s tally, such as &ldquo;yeas 10, nays 2 (Flynn,
            Murphy)&rdquo;. Of the <strong>{fmt(summary.stated_tally)}</strong> that state one, <strong>{fmt(flagged.length)}</strong> list
            votes that don&apos;t match it. The record doesn&apos;t say which side is right, so both are shown, unchanged.
          </p>
        </div>
      </div>
      <section className="card">
        <div className="card-body" style={{ paddingTop: 8 }}>
          <ul className="rows">
            {flagged.map((r) => (
              <li key={r.id}>
                <Link href={`/votes/${r.id}/`} className="vote-row" style={{ alignItems: "start" }}>
                  <Strip rc={r} />
                  <span>
                    <span className="vote-title">{r.title}</span>
                    <span className="vote-sub">{shortDate(r.date)} · Docket {r.docket}</span>
                    <span className="vote-sub" style={{ color: "var(--warn)" }}>{r.problems.join(" ")}</span>
                  </span>
                  <span className="tally"><b>{r.counts.yes}</b> yes · <span className={r.counts.no ? "no" : ""}>{r.counts.no}</span> no</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  )
}
