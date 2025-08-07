"use client"

import AppShell from "@/components/app-shell"
import ItemCard, { type UIItem } from "@/components/items/item-card"
import { useMemo, useState } from "react"

const base: UIItem[] = Array.from({ length: 24 }).map((_, i) => ({
  id: `it-${i}`,
  title: ["Air Force 1", "Ultraboost Light", "Overshirt", "Slim Chinos"][i % 4] + " " + (i + 1),
  brand: ["Nike", "Adidas", "Zara", "H&M"][i % 4],
  price: Math.round(20 + Math.random() * 180),
  image: "/placeholder.svg",
  condition: "very_good",
  location: ["Paris", "Berlin", "Warsaw", "Madrid"][i % 4],
  seller: Math.round(3 + Math.random() * 2),
  time: `${Math.round(Math.random() * 59)}m ago`,
  url: "https://www.vinted.de/",
  tags: ["summer", "sale", "popular"].slice(0, (i % 3) + 1),
}))

export default function Page() {
  const [filters, setFilters] = useState<{ brands: string[]; price: [number, number] }>({ brands: [], price: [0, 1000] })
  const [view, setView] = useState<"grid" | "list">("grid")

  const items = useMemo(() => {
    return base
      .filter((i) => (filters.brands.length ? filters.brands.includes(i.brand) : true))
      .filter((i) => i.price >= filters.price[0] && i.price <= filters.price[1])
  }, [filters])

  return (
    <AppShell>
      <div className="p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            {items.length} items • {filters.brands.length ? filters.brands.join(", ") : "All brands"}
          </div>
          <div className="flex items-center gap-2">
            <button className={`px-3 py-1 rounded border ${view === 'grid' ? 'bg-[color:var(--vinted-teal)] text-white' : ''}`} onClick={() => setView('grid')}>Grid</button>
            <button className={`px-3 py-1 rounded border ${view === 'list' ? 'bg-[color:var(--vinted-teal)] text-white' : ''}`} onClick={() => setView('list')}>List</button>
          </div>
        </div>

        {view === "grid" ? (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {items.map((it) => (
              <ItemCard key={it.id} item={it} />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((it) => (
              <div key={it.id} className="flex gap-3 rounded-xl bg-white p-3 shadow-sm hover:shadow">
                <div className="relative w-28 aspect-[4/5] overflow-hidden rounded-md">
                  <img src={it.image} alt={it.title} className="w-full h-full object-cover" />
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium">{it.title}</div>
                      <div className="text-xs text-gray-500">{it.brand} • {it.location}</div>
                    </div>
                    <div className="text-[color:var(--vinted-teal)] font-bold">{it.price}€</div>
                  </div>
                  <div className="mt-2">
                    <div className="flex gap-1 text-xs text-gray-500">
                      {it.tags?.map((t) => <span key={t} className="bg-gray-100 rounded px-2 py-0.5">{t}</span>)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}