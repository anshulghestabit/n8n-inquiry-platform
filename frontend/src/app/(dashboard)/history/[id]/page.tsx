'use client'

import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ApiRequestError, API_BASE_URL, apiFetch } from '@/lib/api'

type AgentLog = {
  id: string
  agent_role: string
  status: 'success' | 'failed' | 'skipped'
  duration_ms: number
  output?: Record<string, unknown> | null
  error_message?: string | null
}

type ExecutionDetail = {
  id: string
  workflow_id: string
  source_channel: string
  status: string
  sender_id?: string | null
  inquiry_snippet?: string | null
  final_reply?: string | null
  score?: number | null
  started_at: string
  finished_at?: string | null
  duration_ms?: number | null
  agent_logs: AgentLog[]
}

export default function HistoryDetailPage() {
  const params = useParams<{ id: string }>()
  const [execution, setExecution] = useState<ExecutionDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch<ExecutionDetail>(`/executions/${params.id}`)
      .then(setExecution)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load execution'))
  }, [params.id])

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Execution detail</p>
          <h1>{execution ? `Execution ${execution.id}` : 'Loading execution...'}</h1>
          <p>Trace, reply, and exports for this workflow run.</p>
        </div>
        <div className="row-actions">
          <a className="button secondary" href={`${API_BASE_URL}/executions/${params.id}/export?format=json`} rel="noreferrer" target="_blank">JSON</a>
          <a className="button secondary" href={`${API_BASE_URL}/executions/${params.id}/export?format=txt`} rel="noreferrer" target="_blank">TXT</a>
          <a className="button secondary" href={`${API_BASE_URL}/executions/${params.id}/export?format=pdf`} rel="noreferrer" target="_blank">PDF</a>
        </div>
      </header>

      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}

      {execution ? (
        <>
          <section className="grid" style={{ marginBottom: '1rem' }}>
            <article className="panel">
              <h2>Status</h2>
              <div className="metric">{execution.status}</div>
              <p className="muted">Source: {execution.source_channel}</p>
            </article>
            <article className="panel">
              <h2>Duration</h2>
              <div className="metric">{execution.duration_ms ? `${(execution.duration_ms / 1000).toFixed(2)}s` : '-'}</div>
              <p className="muted">Started: {new Date(execution.started_at).toLocaleString()}</p>
            </article>
            <article className="panel">
              <h2>Score</h2>
              <div className="metric">{execution.score ?? '-'}</div>
              <p className="muted">Sender: {execution.sender_id || '-'}</p>
            </article>
          </section>

          <section className="panel" style={{ marginBottom: '1rem' }}>
            <h2>Inquiry</h2>
            <p className="muted">{execution.inquiry_snippet || 'No inquiry text saved for this run.'}</p>
            <h3 style={{ marginTop: '1rem' }}>Final reply</h3>
            <p className="muted">{execution.final_reply || 'No final reply logged yet.'}</p>
          </section>

          <section className="panel">
            <h2>Agent trace</h2>
            <div className="list-stack">
              {execution.agent_logs.length === 0 ? <p className="muted">No agent logs available.</p> : null}
              {execution.agent_logs.map((log) => (
                <article className="list-row" key={log.id}>
                  <div>
                    <strong>{log.agent_role}</strong>
                    <p className="muted">{log.status} · {log.duration_ms}ms</p>
                    {log.output ? <p className="muted">{JSON.stringify(log.output)}</p> : null}
                    {log.error_message ? <p className="muted">Error: {log.error_message}</p> : null}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </>
  )
}
