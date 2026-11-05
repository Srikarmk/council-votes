// Everything the pages show comes from these three files, written by the Python build (src/councilvotes/build.py).
import rollcallsJson from "@/data/rollcalls.json"
import councillorsJson from "@/data/councillors.json"
import summaryJson from "@/data/summary.json"

export type VoteKind = "yes" | "no" | "present" | "abstain" | "absent" | "choice" | "unknown"
export type Counts = { yes: number; no: number; present: number; abstain: number; absent: number }

export interface RollCall {
  id: string
  date: string
  docket: string
  title: string
  outcome: string
  description: string
  counts: Counts
  election: boolean
  split: boolean
  votes: [string, VoteKind, string?][]
  notes: string[]
  problems: string[]
  dataset_differs: string[]
  roster: string[]
  title_source: "city" | "description"
  source: "bostongov" | "opendata"
  source_url: string
}

export interface Councillor {
  id: string
  name: string
  first: string
  last: string
  shares_name: boolean
  roll_calls: number
  votes: Counts
  split_votes: number
  against_majority: number
  agreement: Record<string, { n: number; same: number }>
}

export interface Summary {
  generated: string
  roll_calls: number
  first: string
  latest: string
  split: number
  stated_tally: number
  inconsistent: number
  notes: number
  compared_with_dataset: number
  dataset_differs: number
  dataset_duplicates: number
  roster_outliers: number
  sources: { name: string; url: string; roll_calls: number; through: string | null; licence?: string }[]
}

export const rollcalls = rollcallsJson as unknown as RollCall[]
export const councillors = councillorsJson as unknown as Councillor[]
export const summary = summaryJson as unknown as Summary

const byId = new Map(councillors.map((c) => [c.id, c]))
const rcById = new Map(rollcalls.map((r) => [r.id, r]))

export const rollcall = (id: string) => rcById.get(id)
export const councillor = (id: string) => byId.get(id)

/** "Murphy", or "Murphy (2021–2024)" when the surname belongs to more than one stretch of years. */
export function nameOf(id: string): string {
  const c = byId.get(id)
  if (!c) return id === "unidentified" ? "Unidentified" : id
  return c.shares_name ? `${c.name} (${c.first.slice(0, 4)}–${c.last.slice(0, 4)})` : c.name
}

/** Votes in a fixed order, alphabetical by name, so a strip's squares line up between roll calls. */
export function seated(r: RollCall) {
  return [...r.votes].sort((a, b) => nameOf(a[0]).localeCompare(nameOf(b[0])))
}

export const LETTER: Record<VoteKind, string> = {
  yes: "y", no: "n", present: "p", abstain: "a", absent: "x", choice: "c", unknown: "u",
}

export const VOTE_WORD: Record<VoteKind, string> = {
  yes: "Yes", no: "No", present: "Present", abstain: "Abstained", absent: "Not present", choice: "Voted for", unknown: "Unclear",
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

export function longDate(d: string): string {
  const [y, m, day] = d.split("-").map(Number)
  return `${MONTHS[m - 1]} ${day}, ${y}`
}

export function shortDate(d: string): string {
  const [y, m, day] = d.split("-").map(Number)
  return `${MONTHS[m - 1].slice(0, 3)} ${day}, ${y}`
}

export const fmt = (n: number) => n.toLocaleString("en-US")
export const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)}%` : "–")

/** The councillors in the latest meeting's roll calls: the council as the data last saw it. */
export function currentCouncil(): Councillor[] {
  const latest = rollcalls.filter((r) => r.date === summary.latest)
  const ids = new Set(latest.flatMap((r) => r.votes.map((v) => v[0])))
  return councillors.filter((c) => ids.has(c.id)).sort((a, b) => a.name.localeCompare(b.name))
}

export function meetings(): { date: string; rolls: RollCall[] }[] {
  const out: { date: string; rolls: RollCall[] }[] = []
  for (const r of rollcalls) {
    if (!out.length || out[out.length - 1].date !== r.date) out.push({ date: r.date, rolls: [] })
    out[out.length - 1].rolls.push(r)
  }
  return out
}

/** A record to look at twice: its votes contradict its own tally, or it lists an older roster. */
export const doubtful = (r: RollCall) => r.problems.length > 0 || r.roster.length > 0

export function listNames(ids: string[]): string {
  const n = ids.map(nameOf)
  return n.length < 2 ? n.join("") : `${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`
}

export function tallyText(c: Counts): string {
  const parts = [`${c.yes} yes`, `${c.no} no`]
  if (c.present) parts.push(`${c.present} present`)
  if (c.abstain) parts.push(`${c.abstain} abstained`)
  if (c.absent) parts.push(`${c.absent} not present`)
  return parts.join(", ")
}
