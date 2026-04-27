'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'

type Summary = {
  total_executions: number
  success_rate: number
  avg_duration_ms: number
  avg_score: number
}

type Execution = {
  id: string
  status: 'running' | 'paused' | 'success' | 'failed' | 'cancelled'
  started_at?: string
  duration_ms?: number | null
  inquiry_snippet?: string | null
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [latest, setLatest] = useState<Execution | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([apiFetch<Summary>('/analytics/summary'), apiFetch<Execution[]>('/executions?limit=1')])
      .then(([summaryData, executionRows]) => {
        setSummary(summaryData)
        setLatest(executionRows[0] || null)
      })
      .catch((err) => {
        setError(err instanceof ApiRequestError ? err.message : 'Unable to load dashboard metrics')
      })
  }, [])

  const avgHandlingTime = useMemo(() => {
    if (!summary) {
      return '--'
    }
    return `${(summary.avg_duration_ms / 1000).toFixed(2)}s`
  }, [summary])

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Demo control room</p>
          <h1>Customer Inquiry Handler</h1>
          <p>Live operations summary for executions, reliability, and the most recent run.</p>
        </div>
        <div className="row-actions">
          <Link className="button" href="/workflows">Create workflow</Link>
          <Link className="button secondary" href="/history">Run test inquiry</Link>
        </div>
      </header>

      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}

      <section className="grid">
        <article className="panel">
          <h2>Processed inquiries</h2>
          <div className="metric">{summary?.total_executions ?? '--'}</div>
          <p className="muted">Total execution runs captured in history.</p>
        </article>
        <article className="panel">
          <h2>Success rate</h2>
          <div className="metric">{summary ? `${summary.success_rate}%` : '--'}</div>
          <p className="muted">Percent of executions that completed successfully.</p>
        </article>
        <article className="panel">
          <h2>Avg handling time</h2>
          <div className="metric">{avgHandlingTime}</div>
          <p className="muted">Average end-to-end execution duration.</p>
        </article>
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Latest run</h2>
        {!latest ? <p className="muted">No executions yet. Trigger a test inquiry from a workflow.</p> : null}
        {latest ? (
          <div className="list-row">
            <div>
              <strong>{latest.id}</strong>
              <p className="muted">
                {latest.status}
                {latest.started_at ? ` · Started ${new Date(latest.started_at).toLocaleString()}` : ''}
                {latest.duration_ms ? ` · ${(latest.duration_ms / 1000).toFixed(2)}s` : ''}
              </p>
              {latest.inquiry_snippet ? <p className="muted">{latest.inquiry_snippet}</p> : null}
            </div>
          </div>
        ) : null}
      </section>
    </>
  )
}
