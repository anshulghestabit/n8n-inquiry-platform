import { NextRequest } from 'next/server'

const INTERNAL_API_URL = process.env.INTERNAL_API_URL
if (!INTERNAL_API_URL) {
  throw new Error('INTERNAL_API_URL is not configured')
}

/**
 * Proxies same-origin Next.js API calls to the internal FastAPI service.
 *
 * @param request - Incoming browser request handled by Next.js.
 * @param context - Dynamic path segments captured by the route.
 * @returns The backend response with status, body, and headers preserved.
 */
async function proxyRequest(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const { path } = await context.params
    const targetUrl = new URL(`/${path.join('/')}${request.nextUrl.search}`, INTERNAL_API_URL)
    const headers = new Headers(request.headers)

    // The Docker service name becomes the authority for internal backend calls.
    headers.delete('host')

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
      redirect: 'manual',
    })

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    })
  } catch {
    return Response.json(
      { detail: { error: 'Backend API unavailable', code: 'API_PROXY_FAILED' } },
      { status: 502 },
    )
  }
}

export const GET = proxyRequest
export const POST = proxyRequest
export const PUT = proxyRequest
export const PATCH = proxyRequest
export const DELETE = proxyRequest
export const OPTIONS = proxyRequest
