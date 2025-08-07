"use client"

import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "./app-sidebar"
import { BottomNav } from "./bottom-nav"

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="pb-16 md:pb-0">
        <header className="flex h-14 items-center gap-2 border-b bg-white/60 backdrop-blur-md px-3 md:px-6">
          <SidebarTrigger />
          <div className="text-sm text-gray-500">Vinted Notifications Bot</div>
          <div className="ml-auto flex items-center gap-2"></div>
        </header>
        <main className="min-h-[calc(100svh-56px)]">{children}</main>
      </SidebarInset>
      <BottomNav />
    </SidebarProvider>
  )
}