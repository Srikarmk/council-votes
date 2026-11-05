import Link from "next/link"
import { LETTER, nameOf, seated, shortDate, VOTE_WORD, type RollCall } from "@/lib/data"

/** One square per councillor, alphabetical: ink for yes, the hue for no, an outline for present or
 *  abstained, pale for not present. */
export function Strip({ rc, big = false }: { rc: RollCall; big?: boolean }) {
  const votes = seated(rc)
  const label = votes.map(([id, v]) => `${nameOf(id)}: ${VOTE_WORD[v].toLowerCase()}`).join(", ")
  return (
    <span className={big ? "strip big" : "strip"} role="img" aria-label={label}>
      {votes.map(([id, v], i) => <i key={`${id}-${i}`} className={LETTER[v]} title={`${nameOf(id)}: ${VOTE_WORD[v]}`} />)}
    </span>
  )
}

export function StripLegend() {
  const kinds: [string, string][] = [["y", "Yes"], ["n", "No"], ["p", "Present or abstained"], ["x", "Not present"]]
  return (
    <div className="legend" aria-hidden="true">
      {kinds.map(([k, w]) => <span key={k}><span className="strip"><i className={k} /></span>{w}</span>)}
    </div>
  )
}

export function Tally({ rc }: { rc: RollCall }) {
  if (rc.election) return <span className="tally">Election</span>
  return (
    <span className="tally">
      <b>{rc.counts.yes}</b> yes · <span className={rc.counts.no ? "no" : ""}>{rc.counts.no}</span> no
    </span>
  )
}

export function VoteRow({ rc, showDate = true, extra }: { rc: RollCall; showDate?: boolean; extra?: React.ReactNode }) {
  const noes = rc.votes.filter((v) => v[1] === "no").map((v) => nameOf(v[0]))
  return (
    <Link href={`/votes/${rc.id}/`} className="vote-row">
      <Strip rc={rc} />
      <span>
        <span className="vote-title">{rc.title}</span>
        <span className="vote-sub">
          {showDate ? `${shortDate(rc.date)} · ` : ""}Docket {rc.docket}
          {noes.length > 0 && !rc.election ? <> · <span className="no-ink">No: {noes.join(", ")}</span></> : null}
          {rc.problems.length > 0 ? <> · <span className="flag">Contradicts itself</span></>
            : rc.roster.length > 0 ? <> · <span className="flag">Older roster</span></> : null}
          {extra}
        </span>
      </span>
      <Tally rc={rc} />
    </Link>
  )
}
