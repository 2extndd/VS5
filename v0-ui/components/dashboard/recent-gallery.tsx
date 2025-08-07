"use client"

import Image from "next/image"

const items = Array.from({ length: 6 }).map((_, i) => ({
  id: i,
  title: `Item ${i + 1}`,
  brand: ["Nike", "Adidas", "Zara"][i % 3],
  price: Math.round(20 + Math.random() * 200),
  image: `/placeholder.svg?height=500&width=400&query=preview%204:5`,
}))

export default function RecentGallery() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {items.map((item) => (
        <div key={item.id} className="group relative aspect-[4/5] overflow-hidden rounded-xl shadow hover:shadow-lg transition-all">
          <Image src={item.image} alt={item.title} fill className="object-cover" />
          <div className="absolute top-2 left-2 bg-[color:var(--vinted-teal)] text-white px-2 py-0.5 rounded-full text-xs">
            {item.price}€
          </div>
          <div className="absolute bottom-2 left-2 right-2 text-xs text-white/90">
            <div className="line-clamp-1">{item.title}</div>
          </div>
        </div>
      ))}
    </div>
  )
}