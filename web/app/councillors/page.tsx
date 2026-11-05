import Link from "next/link"
import { councillors, currentCouncil, fmt, nameOf, pct } from "@/lib/data"

export const metadata = { title: "Councillors" }

export default function Councillors() {
  const now = new Set(currentCouncil().map((c) => c.id))
  const rows = [...councillors].sort((a, b) => b.last.localeCompare(a.last) || a.name.localeCompare(b.name))
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Councillors</h1>
          <p className="lede">
            {fmt(councillors.length)} councillors appear in the record, most recent first. {now.size} voted in the latest meeting.
            Losing side counts the split votes where a councillor voted with the minority.
          </p>
        </div>
      </div>
      <section className="card">
        <div className="card-body" style={{ paddingTop: 18 }}>
          <table>
            <thead>
              <tr>
                <th>Councillor</th><th>In the record</th><th className="r">Roll calls</th><th className="r">Voted no</th>
                <th className="r hide-phone">Losing side</th><th className="r hide-phone">Not present</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td><Link href={`/councillors/${c.id}/`}>{nameOf(c.id)}</Link>{now.has(c.id) ? <span className="muted small"> · latest meeting</span> : null}</td>
                  <td className="muted">{c.first.slice(0, 4)}{c.first.slice(0, 4) !== c.last.slice(0, 4) ? `–${c.last.slice(0, 4)}` : ""}</td>
                  <td className="r">{fmt(c.roll_calls)}</td>
                  <td className="r">{c.votes.no ? <span className="no-ink">{fmt(c.votes.no)}</span> : <span className="dash">0</span>}</td>
                  <td className="r hide-phone">{c.split_votes ? `${fmt(c.against_majority)} of ${fmt(c.split_votes)}` : <span className="dash">–</span>}</td>
                  <td className="r hide-phone">{c.votes.absent ? `${fmt(c.votes.absent)} (${pct(c.votes.absent, c.roll_calls)})` : <span className="dash">0</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
