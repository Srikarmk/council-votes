import Link from "next/link"
import { notFound } from "next/navigation"
import { StripLegend, VoteRow } from "@/components/strip"
import { councillor, councillors, fmt, LETTER, longDate, nameOf, pct, rollcalls, shortDate, VOTE_WORD } from "@/lib/data"

export const dynamicParams = false

export function generateStaticParams() {
  return councillors.map((c) => ({ id: c.id }))
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const c = councillor((await params).id)
  return c ? { title: nameOf(c.id), description: `How ${c.name} voted on the Boston City Council, ${c.first.slice(0, 4)}–${c.last.slice(0, 4)}.` } : {}
}

export default async function Person({ params }: { params: Promise<{ id: string }> }) {
  const c = councillor((await params).id)
  if (!c) notFound()
  const mine = rollcalls.filter((r) => r.votes.some((v) => v[0] === c.id))
  const vote = (r: (typeof mine)[number]) => r.votes.find((v) => v[0] === c.id)![1]
  const noes = mine.filter((r) => vote(r) === "no" && !r.election)
  const byYear = new Map<string, typeof mine>()
  for (const r of [...mine].reverse()) {
    const y = r.date.slice(0, 4)
    byYear.set(y, [...(byYear.get(y) ?? []), r])
  }
  const allies = Object.entries(c.agreement)
    .map(([id, a]) => ({ id, ...a, share: a.same / a.n }))
    .sort((a, b) => b.share - a.share || b.n - a.n)
  const decided = c.votes.yes + c.votes.no
  return (
    <>
      <div className="crumbs"><Link href="/councillors/">Councillors</Link></div>
      <div className="title-row">
        <div>
          <h1>{nameOf(c.id)}</h1>
          <p className="lede">
            Voted in <strong>{fmt(c.roll_calls)} roll calls</strong> between {longDate(c.first)} and {longDate(c.last)}.
            {c.split_votes ? <> On the {fmt(c.split_votes)} that split the Council, voted with the minority {fmt(c.against_majority)} times.</> : null}
          </p>
          {c.shares_name && (
            <p className="lede small">The City&apos;s records give surnames only. This surname appears in more than one stretch of years, which are listed separately because they may be different councillors.</p>
          )}
        </div>
        <Link className="btn btn-secondary" href={`/votes/?who=${c.id}`}>All {fmt(c.roll_calls)} votes</Link>
      </div>

      <div className="stack">
        <section className="card figures" aria-label="Voting record in numbers">
          <div className="figure"><span className="kpi">{fmt(c.votes.yes)}</span><span className="label">yes votes ({pct(c.votes.yes, decided)} of yes or no)</span></div>
          <div className="figure"><span className="kpi hue">{fmt(c.votes.no)}</span><span className="label">no votes</span></div>
          <div className="figure"><span className="kpi">{fmt(c.against_majority)}</span><span className="label">times on the losing side of a split vote</span></div>
          <div className="figure"><span className="kpi">{fmt(c.votes.absent)}</span><span className="label">roll calls not present{c.votes.present + c.votes.abstain ? `; ${c.votes.present + c.votes.abstain} present or abstained` : ""}</span></div>
        </section>

        <section className="card">
          <div className="card-head"><h2>Every vote, year by year</h2><span className="meta">one mark per roll call, oldest first</span></div>
          <div className="card-body">
            <table>
              <tbody>
                {[...byYear.entries()].map(([y, rs]) => (
                  <tr key={y}>
                    <td style={{ width: 56 }} className="muted">{y}</td>
                    <td>
                      <span className="strip" style={{ flexWrap: "wrap", rowGap: 3 }}>
                        {rs.map((r) => {
                          const v = vote(r)
                          return (
                            <Link key={r.id} href={`/votes/${r.id}/`} aria-label={`${shortDate(r.date)}, docket ${r.docket}: ${VOTE_WORD[v]}`}
                              title={`${shortDate(r.date)} · Docket ${r.docket}: ${VOTE_WORD[v]}`} style={{ display: "contents" }}>
                              <i className={LETTER[v]} />
                            </Link>
                          )
                        })}
                      </span>
                    </td>
                    <td className="r small muted" style={{ width: 120 }}>
                      {rs.length} · {rs.filter((r) => vote(r) === "no").length} no
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card-foot"><StripLegend /></div>
        </section>

        <div className="grid">
          <section className="card span-7">
            <div className="card-head">
              <h2>Voted no</h2>
              {noes.length > 8 && <Link className="meta" href={`/votes/?who=${c.id}&split=1`}>All split votes</Link>}
            </div>
            <div className="card-body">
              {noes.length ? <ul className="rows">{noes.slice(0, 8).map((r) => <li key={r.id}><VoteRow rc={r} /></li>)}</ul>
                : <p className="empty" style={{ padding: "8px 0 0" }}>{c.name} voted yes on every roll call they voted in.</p>}
            </div>
          </section>

          <section className="card span-5">
            <div className="card-head"><h2>Who they vote with</h2><span className="meta">on split votes</span></div>
            <div className="card-body">
              {allies.length ? (
                <table>
                  <thead><tr><th>Councillor</th><th>Same vote</th><th className="r">Shared</th></tr></thead>
                  <tbody>
                    {allies.map((a) => (
                      <tr key={a.id}>
                        <td><Link href={`/councillors/${a.id}/`}>{nameOf(a.id)}</Link></td>
                        <td style={{ width: "40%" }}>
                          <span className="bar" title={`${a.same} of ${a.n}`}><i style={{ width: `${Math.round(100 * a.share)}%` }} /></span>
                        </td>
                        <td className="r">{pct(a.same, a.n)} <span className="muted small">of {a.n}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="empty" style={{ padding: "8px 0 0" }}>Fewer than five split votes shared with any colleague, too few to compare.</p>}
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
