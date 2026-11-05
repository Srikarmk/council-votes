import Link from "next/link"
import { notFound } from "next/navigation"
import { Strip, StripLegend } from "@/components/strip"
import { listNames, longDate, nameOf, rollcall, rollcalls, seated, tallyText, VOTE_WORD } from "@/lib/data"

export const dynamicParams = false

export function generateStaticParams() {
  return rollcalls.map((r) => ({ id: r.id }))
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const r = rollcall((await params).id)
  return r ? { title: `Docket ${r.docket}, ${longDate(r.date)}`, description: r.title } : {}
}

export default async function Vote({ params }: { params: Promise<{ id: string }> }) {
  const r = rollcall((await params).id)
  if (!r) notFound()
  const sameDay = rollcalls.filter((x) => x.date === r.date)
  const i = sameDay.findIndex((x) => x.id === r.id)
  return (
    <>
      <div className="crumbs">
        <Link href="/votes/">All votes</Link> / <Link href={`/votes/?date=${r.date}`}>{longDate(r.date)}</Link>
      </div>
      <div className="title-row">
        <div>
          <h1>Docket {r.docket}</h1>
          <p className="lede">
            Roll call {i + 1} of {sameDay.length} at the meeting of {longDate(r.date)}
            {r.election ? "" : <>: <strong>{tallyText(r.counts)}</strong></>}.
          </p>
        </div>
        <a className="btn btn-secondary" href={r.source_url} rel="noopener">
          {r.source === "bostongov" ? "See it on boston.gov" : "See the City's dataset"}
        </a>
      </div>

      <div className="stack">
        {r.problems.length > 0 && (
          <section className="notice" aria-labelledby="mismatch">
            <h2 id="mismatch">This record contradicts itself</h2>
            <p>The votes recorded below don&apos;t match the tally the clerk wrote in the description. Both come from the City; neither has been changed here.</p>
            <ul>{r.problems.map((p) => <li key={p}>{p}</li>)}</ul>
          </section>
        )}

        {r.roster.length > 0 && (
          <section className="notice" aria-labelledby="roster">
            <h2 id="roster">This record may list an older Council</h2>
            <p>
              It lists {listNames(r.roster)}, who {r.roster.length === 1 ? "appears" : "appear"} in fewer than half of the roll
              calls in the three months before and after it. Records like this seem to reuse a previous Council&apos;s
              roster. The votes are shown as the City published them, but left out of {r.roster.length === 1 ? "that councillor's" : "those councillors'"} voting records here.
            </p>
          </section>
        )}

        <div className="grid">
          <section className="card span-7">
            <div className="card-head"><h2>The motion</h2></div>
            <div className="card-body">
              <p className="motion">{r.title}</p>
              {r.title_source === "city" ? <p className="muted small" style={{ marginTop: 4 }}>The City&apos;s own summary of the docket.</p> : null}
              <p className="outcome">{r.outcome}</p>
            </div>
            <div className="card-head" style={{ paddingTop: 8 }}><h2>The clerk&apos;s full description</h2></div>
            <div className="card-body"><p className="prose">{r.description}</p></div>
          </section>

          <section className="card span-5">
            <div className="card-head">
              <h2>{r.election ? "How each councillor voted" : "How each councillor voted"}</h2>
              <span className="meta">{r.votes.length} recorded</span>
            </div>
            <div className="card-body">
              <div style={{ marginBottom: 14 }}><Strip rc={r} big /></div>
              <div className="ballot">
                {seated(r).map(([id, v, choice], i) => {
                  const word = v === "choice" ? `${nameOf(choice ?? "")}` : VOTE_WORD[v]
                  const inner = <><span>{nameOf(id)}</span><span className={`v ${v}`}>{word}</span></>
                  return id === "unidentified"
                    ? <span key={`${id}-${i}`} className="who">{inner}</span>
                    : <Link key={`${id}-${i}`} href={`/councillors/${id}/`}>{inner}</Link>
                })}
              </div>
            </div>
            <div className="card-foot"><StripLegend /></div>
          </section>
        </div>

        {r.dataset_differs.length > 0 && (
          <section className="card">
            <div className="card-head"><h2>The City&apos;s open dataset records this vote differently</h2></div>
            <div className="card-body notes">
              <p>This page follows boston.gov. The City&apos;s 2008–2024 dataset has the same roll call with these differences:</p>
              <ul>{r.dataset_differs.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
          </section>
        )}

        {r.notes.length > 0 && (
          <section className="card">
            <div className="card-head"><h2>How this record was read</h2></div>
            <div className="card-body notes">
              <p>The City&apos;s data gives surnames and short vote codes. These changes were made to read it, and nothing else:</p>
              <ul>{r.notes.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
          </section>
        )}
      </div>
    </>
  )
}
