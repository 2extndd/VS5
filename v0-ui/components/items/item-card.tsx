"use client"

export type UIItem = {
  id: string
  title: string
  brand: string
  price: number
  image: string
  condition: string
  location: string
  seller: number
  time: string
  url: string
  tags: string[]
}

export default function ItemCard({ item }: { item: UIItem }) {
  return (
    <a href={item.url} target="_blank" rel="noreferrer" className="group relative bg-white rounded-xl shadow hover:shadow-lg transition-all overflow-hidden">
      <div className="aspect-[4/5] relative">
        <img src={item.image} alt={item.title} className="w-full h-full object-cover" />
        <div className="absolute top-2 left-2 bg-[color:var(--vinted-teal)] text-white px-2 py-0.5 rounded-full text-xs">
          {item.price}€
        </div>
        <div className="absolute bottom-2 left-2 right-2 text-xs text-white/90">
          <div className="line-clamp-1">{item.brand}</div>
        </div>
      </div>
      <div className="p-2">
        <div className="text-sm font-medium line-clamp-1">{item.title}</div>
      </div>
    </a>
  )
}