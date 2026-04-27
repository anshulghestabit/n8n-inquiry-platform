import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export default async function HomePage() {
  const token = (await cookies()).get('auth-token')?.value
  redirect(token ? '/dashboard' : '/login')
}
