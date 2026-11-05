import type { Metadata } from "next"
import { Shell } from "@/components/shell"
import { fmt, longDate, rollcalls, summary } from "@/lib/data"
import "./globals.css"

export const metadata: Metadata = {
  title: { default: "Yeas & Nays: Boston City Council votes", template: "%s · Yeas & Nays" },
  description: "Every recorded roll-call vote of the Boston City Council since 2008: how each councillor voted, "
    + "where the Council split, and where the City's own records contradict themselves.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const flagged = rollcalls.filter((r) => r.problems.length).length
  const items = [
    { href: "/", label: "Latest" },
    { href: "/votes/", label: "All votes", count: fmt(summary.roll_calls) },
    { href: "/councillors/", label: "Councillors" },
    { href: "/contradictions/", label: "Contradictions", count: fmt(flagged) },
    { href: "/about/", label: "About the data" },
  ]
  const foot = (
    <>
      <p>Votes from {longDate(summary.first)} to {longDate(summary.latest)}, from the City of Boston&apos;s published records.</p>
      <p>An independent project, not affiliated with or endorsed by the City of Boston.</p>
    </>
  )
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <Shell items={items} foot={foot}>{children}</Shell>
      </body>
    </html>
  )
}
