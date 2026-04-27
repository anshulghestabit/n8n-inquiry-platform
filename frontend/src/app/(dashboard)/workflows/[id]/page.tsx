'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
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

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>()
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch<Workflow>(`/workflows/${params.id}`)
      .then(setWorkflow)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load workflow'))
  }, [params.id])

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
      {workflow ? (
        <section className="grid">
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
      ) : null}
    </>
  )
}
