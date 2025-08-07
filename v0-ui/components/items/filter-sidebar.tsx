"use client"

export default function FilterSidebar({ onChange }: { onChange: (filters: any) => void }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-medium mb-1">Brands</div>
        <input className="w-full border rounded px-2 py-1" placeholder="Comma-separated brands" onBlur={(e) => {
          const brands = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
          onChange((prev: any) => ({ ...prev, brands }))
        }} />
      </div>
      <div>
        <div className="text-sm font-medium mb-1">Price Range</div>
        <div className="flex gap-2">
          <input className="w-full border rounded px-2 py-1" type="number" placeholder="Min" onBlur={(e) => onChange((prev: any) => ({ ...prev, price: [Number(e.target.value) || 0, prev?.price?.[1] ?? 1000] }))} />
          <input className="w-full border rounded px-2 py-1" type="number" placeholder="Max" onBlur={(e) => onChange((prev: any) => ({ ...prev, price: [prev?.price?.[0] ?? 0, Number(e.target.value) || 1000] }))} />
        </div>
      </div>
    </div>
  )
}