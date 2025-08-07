"use client"

import React from "react"

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen flex">{children}</div>
}

export function SidebarInset({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`flex-1 ${className}`}>{children}</div>
}

export function SidebarTrigger() {
  return <button className="px-3 py-1 border rounded text-xs">Menu</button>
}