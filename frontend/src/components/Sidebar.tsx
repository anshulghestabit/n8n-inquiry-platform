'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', marker: '01' },
  { href: '/workflows', label: 'Workflows', marker: '02' },
  { href: '/settings/integrations', label: 'Integrations', marker: '03' },
  { href: '/history', label: 'History', marker: '04' },
  { href: '/analytics', label: 'Analytics', marker: '05' },
  { href: '/profile', label: 'Profile', marker: '06' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout, loading } = useAuth()

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">n8n</div>
        <div>
          <strong>Inquiry Platform</strong>
          <span>Multi-agent console</span>
        </div>
      </div>

      <nav className="nav-list" aria-label="Dashboard navigation">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
          return (
            <Link key={item.href} className={`nav-link${active ? ' active' : ''}`} href={item.href}>
              <span>{item.label}</span>
              <span>{item.marker}</span>
            </Link>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <p className="muted">Signed in as</p>
        <strong>{loading ? 'Loading...' : user?.email || 'Unknown user'}</strong>
        <button className="button secondary" style={{ width: '100%', marginTop: '1rem' }} onClick={logout}>
          Logout
        </button>
      </div>
    </aside>
  )
}
