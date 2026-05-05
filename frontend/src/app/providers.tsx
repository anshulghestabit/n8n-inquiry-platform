'use client'

import { AuthProvider } from '@/lib/auth-context'

/**
 * Installs client-side providers required by the application shell.
 *
 * @param props - Provider props.
 * @param props.children - React subtree rendered by the root layout.
 * @returns Application providers wrapping the subtree.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}
