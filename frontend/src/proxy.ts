import { NextRequest, NextResponse } from 'next/server'

const protectedRoutes = ['/dashboard', '/workflows', '/history', '/analytics', '/settings', '/profile']
const authRoutes = ['/login', '/register']

/**
 * Enforces cookie-based route access before dashboard pages render.
 *
 * @param request - Incoming Next.js request.
 * @returns Redirects unauthenticated/authenticated users or allows the request.
 */
export function proxy(request: NextRequest) {
  const token = request.cookies.get('auth-token')?.value
  const path = request.nextUrl.pathname

  const isProtected = protectedRoutes.some((route) => path.startsWith(route))
  const isAuth = authRoutes.some((route) => path.startsWith(route))

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isAuth && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

/** Next.js middleware matcher excluding API, static asset, and favicon requests. */
export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
