import { Suspense } from "react"
import { VoteSearch } from "@/components/vote-search"
import { councillors, fmt, nameOf, summary } from "@/lib/data"

export const metadata = { title: "All votes" }

export default function Votes() {
  const people = councillors.map((c) => ({ id: c.id, name: nameOf(c.id) })).sort((a, b) => a.name.localeCompare(b.name))
  const years = Array.from({ length: +summary.latest.slice(0, 4) - +summary.first.slice(0, 4) + 1 },
    (_, i) => String(+summary.latest.slice(0, 4) - i))
  return (
    <>
      <div className="title-row">
        <div>
          <h1>All votes</h1>
          <p className="lede">
            {fmt(summary.roll_calls)} roll calls, newest first. Search the motions, or narrow to a year, a councillor,
            split votes or records that contradict themselves.
          </p>
        </div>
      </div>
      <Suspense fallback={<div className="card"><p className="empty">Loading the votes…</p></div>}>
        <VoteSearch people={people} years={years} />
      </Suspense>
    </>
  )
}
