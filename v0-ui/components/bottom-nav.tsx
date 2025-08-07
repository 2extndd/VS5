"use client"

import Link from "next/link"

export function BottomNav() {
  return (
    <nav className="fixed md:hidden bottom-0 inset-x-0 bg-white/90 backdrop-blur border-t">
      <div className="grid grid-cols-5 text-xs text-center">
        <Link href="/" className="py-2">Home</Link>
        <Link href="/queries" className="py-2">Queries</Link>
        <Link href="/items" className="py-2">Items</Link>
        <Link href="/analytics" className="py-2">Stats</Link>
        <Link href="/config" className="py-2">Config</Link>
      </div>
    </nav>
  )
}