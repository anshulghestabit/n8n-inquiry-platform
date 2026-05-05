import { Sidebar } from '@/components/Sidebar'
import { StatusBar } from '@/components/StatusBar'

/**
 * Shared dashboard chrome for authenticated pages.
 *
 * @param props - Layout props.
 * @param props.children - Dashboard route content.
 * @returns Dashboard shell with navigation and integration status.
 */
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
