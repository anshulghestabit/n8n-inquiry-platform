import { Sidebar } from '@/components/Sidebar'
import { StatusBar } from '@/components/StatusBar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="main-area">
        <StatusBar />
        <div className="content">{children}</div>
      </main>
    </div>
  )
}
