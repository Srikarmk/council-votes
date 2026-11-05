"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"

type Item = { href: string; label: string; count?: string }

function Brand() {
  return (
    <Link href="/" className="brand" aria-label="Yeas & Nays, home">
      <span className="brand-mark" aria-hidden="true"><i /><i /></span>
      <span>
        <span className="brand-name">Yeas &amp; Nays</span>
        <span className="brand-scope">Boston City Council votes</span>
      </span>
    </Link>
  )
}

export function Shell({ items, foot, children }: { items: Item[]; foot: React.ReactNode; children: React.ReactNode }) {
  const path = usePathname()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [path])
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href))
  const current = items.find((i) => active(i.href))?.label ?? "Yeas & Nays"
  return (
    <div className="shell">
      <header className="topbar">
        <Brand />
        <button className="menu-btn" aria-expanded={open} aria-controls="nav" onClick={() => setOpen(!open)}>
          {open ? "Close" : current}
        </button>
      </header>
      <aside id="nav" className={open ? "sidebar open" : "sidebar"}>
        <div className="hide-phone"><Brand /></div>
        <nav className="nav" aria-label="Main">
          {items.map((i) => (
            <Link key={i.href} href={i.href} aria-current={active(i.href) ? "page" : undefined}>
              <span>{i.label}</span>
              {i.count ? <span className="count">{i.count}</span> : null}
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">{foot}</div>
      </aside>
      <main className="canvas">{children}</main>
    </div>
  )
}
