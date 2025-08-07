import AppShell from "@/components/app-shell"
import RecentGallery from "@/components/dashboard/recent-gallery"

export default function Page() {
  return (
    <AppShell>
      <div className="p-4 md:p-6 space-y-4">
        <RecentGallery />
      </div>
    </AppShell>
  )
}