'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { FormEvent, useEffect, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'

type Agent = {
  id: string
  name: string
  role: string
  system_prompt: string
  order_index: number
}

type Workflow = {
  id: string
  name: string
  description?: string | null
  trigger_channel: string
  status: string
  n8n_workflow_id?: string | null
  agents: Agent[]
}

type AgentLog = {
  id?: string
  agent_role: string
  status: 'success' | 'failed' | 'skipped'
  duration_ms: number
  output?: Record<string, unknown> | null
  error_message?: string | null
}

type ExecutionStatus = {
  id: string
  status: 'running' | 'paused' | 'success' | 'failed' | 'cancelled'
  duration_ms?: number | null
  finished_at?: string | null
  trace: AgentLog[]
}

const roleLabels: Record<string, string> = {
  classifier: 'Classifier',
  researcher: 'Researcher',
  qualifier: 'Qualifier',
  responder: 'Responder',
  executor: 'Executor',
}

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>()
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [execution, setExecution] = useState<ExecutionStatus | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    apiFetch<Workflow>(`/workflows/${params.id}`)
      .then(setWorkflow)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load workflow'))
  }, [params.id])

  useEffect(() => {
    if (!execution?.id || execution.status !== 'running') {
      return
    }

    let active = true
    const timer = window.setInterval(async () => {
      try {
        const latest = await apiFetch<ExecutionStatus>(`/executions/${execution.id}/status`)
        if (active) {
          setExecution(latest)
          if (latest.status !== 'running') {
            setRunning(false)
            setMessage(`Execution ${latest.status}`)
          }
        }
      } catch {
        if (active) {
          setRunning(false)
        }
      }
    }, 2_000)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [execution?.id, execution?.status])

  async function handleRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const inquiryText = String(formData.get('inquiry_text') || '')

    setError('')
    setMessage('')
    setRunning(true)

    try {
      const triggered = await apiFetch<{ execution_id: string; status: ExecutionStatus['status'] }>(
        `/executions/trigger/${params.id}`,
        {
          method: 'POST',
          body: JSON.stringify({
            inquiry_text: inquiryText,
            source_channel: String(formData.get('source_channel') || 'test'),
            sender_id: String(formData.get('sender_id') || ''),
          }),
        },
      )

      const latest = await apiFetch<ExecutionStatus>(`/executions/${triggered.execution_id}/status`)
      setExecution(latest)
      setMessage('Execution started')
    } catch (err) {
      setRunning(false)
      setError(err instanceof ApiRequestError ? err.message : 'Unable to trigger execution')
    }
  }

  async function handleCancel() {
    if (!execution?.id) {
      return
    }

    setError('')
    try {
      await apiFetch(`/executions/${execution.id}/cancel`, { method: 'POST' })
      const latest = await apiFetch<ExecutionStatus>(`/executions/${execution.id}/status`)
      setExecution(latest)
      setRunning(false)
      setMessage('Execution cancelled')
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to cancel execution')
    }
  }

  async function handleRetry() {
    if (!execution?.id) {
      return
    }

    setError('')
    setMessage('')
    setRunning(true)

    try {
      const retried = await apiFetch<{ execution_id: string }>(`/executions/${execution.id}/retry`, { method: 'POST' })
      const latest = await apiFetch<ExecutionStatus>(`/executions/${retried.execution_id}/status`)
      setExecution(latest)
      setMessage('Retry execution started')
    } catch (err) {
      setRunning(false)
      setError(err instanceof ApiRequestError ? err.message : 'Unable to retry execution')
    }
  }

  async function handlePause() {
    if (!execution?.id) {
      return
    }

    setError('')
    try {
      await apiFetch(`/executions/${execution.id}/pause`, { method: 'POST' })
      const latest = await apiFetch<ExecutionStatus>(`/executions/${execution.id}/status`)
      setExecution(latest)
      setRunning(false)
      setMessage('Execution paused')
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to pause execution')
    }
  }

  async function handleResume() {
    if (!execution?.id) {
      return
    }

    setError('')
    setMessage('')
    setRunning(true)

    try {
      const resumed = await apiFetch<{ execution_id: string }>(`/executions/${execution.id}/resume`, { method: 'POST' })
      const latest = await apiFetch<ExecutionStatus>(`/executions/${resumed.execution_id}/status`)
      setExecution(latest)
      setMessage('Execution resumed')
    } catch (err) {
      setRunning(false)
      setError(err instanceof ApiRequestError ? err.message : 'Unable to resume execution')
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Workflow detail</p>
          <h1>{workflow?.name || 'Loading workflow...'}</h1>
          <p>{workflow?.description || 'Inspect the cloned n8n workflow and configured agents.'}</p>
        </div>
        <div className="row-actions">
          <Link className="button secondary" href={`/workflows/${params.id}/agents`}>Configure agents</Link>
          <Link className="button secondary" href={`/workflows/${params.id}/edit`}>Open n8n editor</Link>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="status-pill" style={{ marginBottom: '1rem' }}><span className="dot ok" />{message}</div> : null}
      {workflow ? (
        <>
          <section className="grid" style={{ marginBottom: '1rem' }}>
            <article className="panel">
              <h2>Status</h2>
              <div className="metric">{workflow.status}</div>
              <p className="muted">Trigger: {workflow.trigger_channel}</p>
            </article>
            <article className="panel">
              <h2>n8n workflow</h2>
              <div className="metric">{workflow.n8n_workflow_id ? 'Linked' : 'Missing'}</div>
              <p className="muted">{workflow.n8n_workflow_id || 'No n8n workflow id saved'}</p>
            </article>
            <article className="panel">
              <h2>Agents</h2>
              <div className="metric">{workflow.agents.length}</div>
              <p className="muted">Expected 5 agents per workflow.</p>
            </article>
          </section>

          <section className="panel" style={{ marginBottom: '1rem' }}>
            <h2>Test inquiry</h2>
            <form className="form-stack" onSubmit={handleRun}>
              <div className="field">
                <label htmlFor="inquiry_text">Inquiry text</label>
                <textarea
                  id="inquiry_text"
                  name="inquiry_text"
                  rows={4}
                  placeholder="Hi team, we are evaluating your Growth and Enterprise plans for 50 users..."
                  required
                />
              </div>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
                <div className="field">
                  <label htmlFor="source_channel">Channel</label>
                  <select id="source_channel" name="source_channel" defaultValue="test">
                    <option value="test">Test</option>
                    <option value="gmail">Gmail</option>
                    <option value="telegram">Telegram</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="sender_id">Sender</label>
                  <input id="sender_id" name="sender_id" placeholder="customer@example.com" />
                </div>
              </div>
              <div className="row-actions">
                <button className="button" disabled={running} type="submit">{running ? 'Running...' : 'Run'}</button>
                <button className="button secondary" disabled={!execution || execution.status !== 'running'} onClick={handleCancel} type="button">Stop</button>
                <button className="button secondary" disabled={!execution || execution.status !== 'running'} onClick={handlePause} type="button">Pause</button>
                <button className="button secondary" disabled={!execution || execution.status !== 'paused'} onClick={handleResume} type="button">Resume</button>
                <button className="button secondary" disabled={!execution} onClick={handleRetry} type="button">Retry</button>
              </div>
            </form>
          </section>

          <section className="panel">
            <h2>Trace</h2>
            {!execution ? <p className="muted">Run an inquiry to populate execution trace.</p> : null}
            {execution ? (
              <>
                <p className="muted" style={{ marginTop: 0 }}>
                  Execution `{execution.id}` - {execution.status}
                  {execution.duration_ms ? ` - ${(execution.duration_ms / 1000).toFixed(2)}s` : ''}
                </p>
                <div className="list-stack">
                  {execution.trace.length === 0 ? <p className="muted">No agent logs yet.</p> : null}
                  {execution.trace.map((log, index) => (
                    <article className="list-row" key={`${log.agent_role}-${index}`}>
                      <div>
                        <strong>{roleLabels[log.agent_role] || log.agent_role}</strong>
                        <p className="muted">
                          {log.status} - {log.duration_ms} ms
                          {log.error_message ? ` - ${log.error_message}` : ''}
                        </p>
                        {log.output ? <p className="muted" style={{ marginTop: '0.4rem' }}>{JSON.stringify(log.output)}</p> : null}
                      </div>
                    </article>
                  ))}
                </div>
              </>
            ) : null}
          </section>
        </>
      ) : null}
    </>
  )
}
