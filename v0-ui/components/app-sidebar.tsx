"use client"

import Link from "next/link"

export function AppSidebar() {
  return (
    <aside className="hidden md:block w-56 border-r bg-white/70 backdrop-blur">
      <nav className="p-4 space-y-2">
        <Link href="/" className="block text-sm">Dashboard</Link>
        <Link href="/items" className="block text-sm">Items</Link>
        <Link href="/queries" className="block text-sm">Queries</Link>
        <Link href="/config" className="block text-sm">Configuration</Link>
        <Link href="/logs" className="block text-sm">Logs</Link>
      </nav>
    </aside>
  )
}