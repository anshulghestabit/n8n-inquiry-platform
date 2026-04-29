'use client'

import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'

type Workflow = {
  id: string
  name: string
  n8n_workflow_id?: string | null
}

export default function WorkflowEditPage() {
  const params = useParams<{ id: string }>()
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [error, setError] = useState('')
  const n8nBaseUrl = process.env.NEXT_PUBLIC_N8N_EDITOR_URL || 'https://n8n.anshul-garg.com'
  const n8nEditorUrl = workflow?.n8n_workflow_id
    ? `${n8nBaseUrl}/#/workflow/${workflow.n8n_workflow_id}`
    : ''

  useEffect(() => {
    apiFetch<Workflow>(`/workflows/${params.id}`)
      .then(setWorkflow)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : 'Unable to load workflow'))
  }, [params.id])

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">n8n editor</p>
          <h1>{workflow?.name || 'Workflow editor'}</h1>
          <p>Open the cloned n8n workflow in the n8n editor.</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {!workflow?.n8n_workflow_id ? <section className="panel"><p className="muted">No n8n workflow id found yet.</p></section> : null}
      {workflow?.n8n_workflow_id ? (
        <section className="panel">
          <h2>Open in n8n</h2>
          <p className="muted">
            n8n blocks embedding in a cross-origin iframe on some local setups, so open the workflow directly in n8n.
          </p>
          <div className="row-actions" style={{ marginTop: '1rem' }}>
            <a className="button" href={n8nEditorUrl} rel="noreferrer" target="_blank">
              Open n8n workflow
            </a>
          </div>
          <p className="muted" style={{ marginTop: '1rem' }}>{n8nEditorUrl}</p>
        </section>
      ) : null}
    </>
  )
}
