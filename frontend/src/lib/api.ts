export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export type ApiError = {
  error: string
  code: string
}

export class ApiRequestError extends Error {
  code: string
  status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
  }
}

type RequestOptions = RequestInit & { skipJson?: boolean }

function errorPayloadValue(payload: unknown, key: 'error' | 'code'): string | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }
  const value = (payload as Record<string, unknown>)[key]
  return typeof value === 'string' ? value : undefined
}

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
