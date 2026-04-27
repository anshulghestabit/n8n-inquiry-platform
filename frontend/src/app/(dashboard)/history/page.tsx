'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ApiRequestError, API_BASE_URL, apiFetch } from '@/lib/api'

type Execution = {
  id: string
  source_channel: string
  status: 'running' | 'success' | 'failed' | 'cancelled'
  inquiry_snippet?: string | null
  duration_ms?: number | null
  score?: number | null
  started_at: string
}

const statusOptions = ['all', 'running', 'success', 'failed', 'cancelled'] as const
const channelOptions = ['all', 'gmail', 'whatsapp', 'test'] as const

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

export default function HistoryPage() {
  const [items, setItems] = useState<Execution[]>([])
  const [statusFilter, setStatusFilter] = useState<(typeof statusOptions)[number]>('all')
  const [channelFilter, setChannelFilter] = useState<(typeof channelOptions)[number]>('all')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const params = new URLSearchParams({ limit: '50' })
    if (statusFilter !== 'all') {
      params.set('status', statusFilter)
    }
    if (channelFilter !== 'all') {
      params.set('source_channel', channelFilter)
    }

    apiFetch<Execution[]>(`/executions?${params.toString()}`)
      .then(setItems)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load history'))
      .finally(() => setLoading(false))
  }, [statusFilter, channelFilter])

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Layer 9</p>
          <h1>Execution History</h1>
          <p>Filter execution runs, inspect trace details, and export analytics data.</p>
        </div>
        <a className="button secondary" href={`${API_BASE_URL}/analytics/export?format=csv`} rel="noreferrer" target="_blank">
          Export CSV
        </a>
      </header>

      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}

      <section className="panel" style={{ marginBottom: '1rem' }}>
        <h2>Filters</h2>
        <div className="row-actions">
          <select
            onChange={(event) => {
              setLoading(true)
              setError('')
              setChannelFilter(event.target.value as (typeof channelOptions)[number])
            }}
            value={channelFilter}
          >
            {channelOptions.map((option) => (
              <option key={option} value={option}>
                Channel: {option}
              </option>
            ))}
          </select>
          <select
            onChange={(event) => {
              setLoading(true)
              setError('')
              setStatusFilter(event.target.value as (typeof statusOptions)[number])
            }}
            value={statusFilter}
          >
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                Status: {option}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="panel">
        <h2>Recent executions</h2>
        {loading ? <p className="muted">Loading execution history...</p> : null}
        {!loading && items.length === 0 ? <p className="muted">No executions found for selected filters.</p> : null}

        <div className="list-stack">
          {items.map((item) => (
            <Link className="list-row" href={`/history/${item.id}`} key={item.id}>
              <div>
                <strong>{formatDate(item.started_at)}</strong>
                <p className="muted">
                  {item.source_channel} · {item.status} · {item.duration_ms ? `${(item.duration_ms / 1000).toFixed(2)}s` : 'pending'} · score {item.score ?? '-'}
                </p>
                <p className="muted">{item.inquiry_snippet || 'No inquiry snippet stored'}</p>
              </div>
              <span className="button secondary">Open</span>
            </Link>
          ))}
        </div>
      </section>
    </>
  )
}
