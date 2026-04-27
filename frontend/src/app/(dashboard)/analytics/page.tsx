'use client'

import { useEffect, useState } from 'react'
import { ApiRequestError, API_BASE_URL, apiFetch } from '@/lib/api'

type Summary = {
  total_executions: number
  success_rate: number
  avg_duration_ms: number
  avg_score: number
  avg_relevance_score: number
  avg_completeness_score: number
}

type AgentMetric = {
  agent_role: string
  avg_duration_ms: number
  success_rate: number
  contribution_pct: number
  bottleneck_flag: boolean
  bottleneck_explanation: string
  sample_size: number
}

type ChartPoint = {
  date: string
  count: number
  success_count: number
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [agents, setAgents] = useState<AgentMetric[]>([])
  const [chart, setChart] = useState<ChartPoint[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      apiFetch<Summary>('/analytics/summary'),
      apiFetch<AgentMetric[]>('/analytics/agents'),
      apiFetch<ChartPoint[]>('/analytics/chart'),
    ])
      .then(([summaryData, agentData, chartData]) => {
        setSummary(summaryData)
        setAgents(agentData)
        setChart(chartData)
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load analytics'))
  }, [])

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Layer 10</p>
          <h1>Analytics</h1>
          <p>Track execution outcomes, trendline counts, and per-agent bottlenecks.</p>
        </div>
        <div className="row-actions">
          <a className="button secondary" href={`${API_BASE_URL}/analytics/export?format=csv`} rel="noreferrer" target="_blank">Export CSV</a>
          <a className="button secondary" href={`${API_BASE_URL}/analytics/export?format=pdf`} rel="noreferrer" target="_blank">Export PDF</a>
        </div>
      </header>

      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}

      <section className="grid">
        <article className="panel">
          <h2>Total executions</h2>
          <div className="metric">{summary?.total_executions ?? '--'}</div>
        </article>
        <article className="panel">
          <h2>Success rate</h2>
          <div className="metric">{summary ? `${summary.success_rate}%` : '--'}</div>
        </article>
        <article className="panel">
          <h2>Avg duration</h2>
          <div className="metric">{summary ? `${(summary.avg_duration_ms / 1000).toFixed(2)}s` : '--'}</div>
        </article>
        <article className="panel">
          <h2>Relevance</h2>
          <div className="metric">{summary ? `${summary.avg_relevance_score}%` : '--'}</div>
        </article>
        <article className="panel">
          <h2>Completeness</h2>
          <div className="metric">{summary ? `${summary.avg_completeness_score}%` : '--'}</div>
        </article>
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Trend</h2>
        <div className="list-stack">
          {chart.length === 0 ? <p className="muted">No trend data yet.</p> : null}
          {chart.map((point) => (
            <div className="list-row" key={point.date}>
              <div>
                <strong>{point.date}</strong>
                <p className="muted">{point.success_count} successful of {point.count} runs</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Agent performance</h2>
        <div className="list-stack">
          {agents.map((agent) => (
            <div className="list-row" key={agent.agent_role}>
              <div>
                <strong>{agent.agent_role}</strong>
                <p className="muted">
                  Avg {agent.avg_duration_ms}ms · Success {agent.success_rate}% · Contribution {agent.contribution_pct}% · Samples {agent.sample_size}
                </p>
                <p className="muted">{agent.bottleneck_explanation}</p>
              </div>
              <span className="status-pill">
                <span className={`dot${agent.bottleneck_flag ? '' : ' ok'}`} />
                {agent.bottleneck_flag ? 'Bottleneck' : 'Healthy'}
              </span>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
