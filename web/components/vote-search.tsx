"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

// One row of public/index.json (written by the Python build): short keys keep the file small.
type Row = {
  id: string; d: string; k: string; t: string
  c: { yes: number; no: number; present: number; abstain: number; absent: number }
  s: 0 | 1; p: 0 | 1 | 2; e: 0 | 1; v: string; w: string[]; x: string
}
type Person = { id: string; name: string }

const PAGE = 50
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
const short = (d: string) => `${MONTHS[+d.slice(5, 7) - 1]} ${+d.slice(8)}, ${d.slice(0, 4)}`
const fold = (s: string) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()

export function VoteSearch({ people, years }: { people: Person[]; years: string[] }) {
  const params = useSearchParams()
  const router = useRouter()
  const [rows, setRows] = useState<Row[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [shown, setShown] = useState(PAGE)
  const name = useMemo(() => new Map(people.map((p) => [p.id, p.name])), [people])

  const q = params.get("q") ?? ""
  const year = params.get("year") ?? ""
  const who = params.get("who") ?? ""
  const date = params.get("date") ?? ""
  const split = params.get("split") === "1"
  const flagged = params.get("flagged") === "1"
  const [text, setText] = useState(q)
  useEffect(() => setText(q), [q])

  useEffect(() => {
    fetch("/index.json").then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then(setRows).catch(() => setFailed(true))
  }, [])

  function set(key: string, value: string) {
    const next = new URLSearchParams(params.toString())
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== "date") next.delete("date")
    setShown(PAGE)
    router.replace(`/votes/${next.size ? `?${next}` : ""}`, { scroll: false })
  }

  const results = useMemo(() => {
    if (!rows) return []
    const words = fold(q).split(/\s+/).filter(Boolean)
    return rows.filter((r) => {
      if (date && r.d !== date) return false
      if (year && !r.d.startsWith(year)) return false
      if (split && !r.s) return false
      if (flagged && !r.p) return false
      if (who && !r.w.includes(who)) return false
      if (words.length) {
        const hay = fold(`${r.t} ${r.x} docket ${r.k} ${r.w.map((w) => name.get(w) ?? w).join(" ")}`)
        return words.every((w) => hay.includes(w))
      }
      return true
    })
  }, [rows, q, year, who, date, split, flagged, name])

  return (
    <section className="card" aria-label="Votes">
      <form className="filters" role="search" onSubmit={(e) => { e.preventDefault(); set("q", text.trim()) }}>
        <input className="field" type="search" aria-label="Search the motions" placeholder="Search the motions"
          value={text} onChange={(e) => setText(e.target.value)} style={{ width: 260 }} />
        <select className="field" aria-label="Year" value={year} onChange={(e) => set("year", e.target.value)}>
          <option value="">Every year</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="field" aria-label="Councillor" value={who} onChange={(e) => set("who", e.target.value)}>
          <option value="">Every councillor</option>
          {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button type="button" className="chip" aria-pressed={split} onClick={() => set("split", split ? "" : "1")}>Split votes</button>
        <button type="button" className="chip" aria-pressed={flagged} onClick={() => set("flagged", flagged ? "" : "1")}>Contradictions</button>
        <span className="result-count" aria-live="polite">
          {rows ? `${results.length.toLocaleString("en-US")} ${results.length === 1 ? "roll call" : "roll calls"}${date ? ` on ${short(date)}` : ""}` : ""}
        </span>
      </form>
      <div className="card-body">
        {failed ? <p className="empty">The votes couldn&apos;t be loaded. Reload the page to try again.</p>
          : !rows ? <p className="empty">Loading the votes…</p>
          : !results.length ? <p className="empty">No roll call matches these filters.</p>
          : (
            <ul className="rows">
              {results.slice(0, shown).map((r) => {
                const seats = r.w.map((w, i) => [w, r.v[i]] as const).sort((a, b) => (name.get(a[0]) ?? a[0]).localeCompare(name.get(b[0]) ?? b[0]))
                const noes = seats.filter((s) => s[1] === "n").map((s) => name.get(s[0]) ?? s[0])
                return (
                  <li key={r.id}>
                    <Link href={`/votes/${r.id}/`} className="vote-row">
                      <span className="strip" aria-hidden="true">{seats.map(([w, v]) => <i key={w} className={v} />)}</span>
                      <span>
                        <span className="vote-title">{r.t}</span>
                        <span className="vote-sub">
                          {short(r.d)} · Docket {r.k}
                          {noes.length && !r.e ? <> · <span className="no-ink">No: {noes.join(", ")}</span></> : null}
                          {r.p ? <> · <span className="flag">{r.p === 1 ? "Contradicts itself" : "Older roster"}</span></> : null}
                        </span>
                      </span>
                      <span className="tally">{r.e ? "Election" : <><b>{r.c.yes}</b> yes · <span className={r.c.no ? "no" : ""}>{r.c.no}</span> no</>}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        {rows && results.length > shown && (
          <div className="pager">
            <button className="btn btn-secondary" onClick={() => setShown(shown + PAGE)}>
              Show {Math.min(PAGE, results.length - shown)} more of {(results.length - shown).toLocaleString("en-US")}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
