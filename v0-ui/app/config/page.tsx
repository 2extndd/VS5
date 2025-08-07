"use client"

import AppShell from "@/components/app-shell"

export default function Page() {
  return (
    <AppShell>
      <div className="p-4 md:p-6 grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl p-4 shadow">
          <h2 className="text-lg font-semibold mb-2">Telegram Bot</h2>
          <div className="space-y-3">
            <div>
              <label className="text-sm">Bot Token</label>
              <input className="w-full border rounded px-3 py-2" placeholder="123456:ABC-DEF1234..." />
            </div>
            <div>
              <label className="text-sm">Default Chat ID</label>
              <input className="w-full border rounded px-3 py-2" placeholder="-1001234567890" />
            </div>
            <button className="px-3 py-2 rounded bg-[color:var(--vinted-teal)] text-white">Save</button>
          </div>
        </section>

        <section className="bg-white rounded-xl p-4 shadow">
          <h2 className="text-lg font-semibold mb-2">Proxy Network</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full" /> Online
            </div>
            <button className="px-3 py-2 rounded border">Test Proxies</button>
          </div>
        </section>

        <section className="bg-white rounded-xl p-4 shadow">
          <h2 className="text-lg font-semibold mb-2">Global Preferences</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm">Currency</label>
              <input className="w-full border rounded px-3 py-2" defaultValue="EUR" />
            </div>
            <div>
              <label className="text-sm">Country Allowlist</label>
              <input className="w-full border rounded px-3 py-2" placeholder="FR, DE, ES, PL" />
            </div>
            <div className="sm:col-span-2">
              <button className="px-3 py-2 rounded bg-[color:var(--vinted-teal)] text-white">Save Preferences</button>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  )
}