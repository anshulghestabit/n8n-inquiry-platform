const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_URL
if (!configuredApiBaseUrl) {
  throw new Error('NEXT_PUBLIC_API_URL is not configured')
}

/** Base URL used by browser-side calls into the FastAPI proxy. */
export const API_BASE_URL = configuredApiBaseUrl

/** Backend error payload shape returned inside FastAPI's `detail` envelope. */
export type ApiError = {
  error: string
  code: string
}

/** Error type used by UI code to branch on API status and machine code. */
export class ApiRequestError extends Error {
  code: string
  status: number

  /**
   * Creates an API request error with both user-facing and machine-readable data.
   *
   * @param message - Human-readable error message.
   * @param code - Backend machine-readable error code.
   * @param status - HTTP status code, or 0 for client-side network failures.
   */
  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
  }
}

type RequestOptions = RequestInit & { skipJson?: boolean }

/**
 * Extracts a string value from a backend error payload.
 *
 * @param payload - Unknown JSON payload returned from the backend.
 * @param key - Error object key to read.
 * @returns The requested string value when present.
 */
function errorPayloadValue(payload: unknown, key: 'error' | 'code'): string | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }
  const value = (payload as Record<string, unknown>)[key]
  return typeof value === 'string' ? value : undefined
}

/**
 * Calls the configured API endpoint with cookie credentials and normalized errors.
 *
 * @typeParam T - Expected JSON response type.
 * @param path - API path under `API_BASE_URL`.
 * @param options - Fetch options passed through to `fetch`.
 * @returns Parsed JSON response typed as `T`.
 * @throws {ApiRequestError} When the request fails, returns non-JSON, or is not OK.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch (error) {
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Network request failed',
      'NETWORK_ERROR',
      0,
    )
  }

  const contentType = response.headers.get('content-type') || ''
  let payload: unknown = null
  if (contentType.includes('application/json')) {
    try {
      payload = await response.json()
    } catch {
      throw new ApiRequestError('Invalid JSON response', 'INVALID_JSON', response.status)
    }
  }

  if (!response.ok) {
    const detail = payload && typeof payload === 'object' && 'detail' in payload
      ? (payload as Record<string, unknown>).detail
      : payload
    throw new ApiRequestError(
      errorPayloadValue(detail, 'error') || 'Request failed',
      errorPayloadValue(detail, 'code') || 'REQUEST_FAILED',
      response.status,
    )
  }

  return payload as T
}
