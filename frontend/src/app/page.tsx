import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

/**
 * Redirects the root route to the correct auth or dashboard destination.
 *
 * @returns Nothing because Next.js short-circuits through `redirect`.
 */
export default async function HomePage() {
  const token = (await cookies()).get('auth-token')?.value
  redirect(token ? '/dashboard' : '/login')
}
