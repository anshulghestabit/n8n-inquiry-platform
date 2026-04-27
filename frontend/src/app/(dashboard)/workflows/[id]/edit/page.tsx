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
          <p>Embedded editor for the cloned n8n workflow.</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {!workflow?.n8n_workflow_id ? <section className="panel"><p className="muted">No n8n workflow id found yet.</p></section> : null}
      {workflow?.n8n_workflow_id ? (
        <iframe
          src={`http://localhost:5678/workflow/${workflow.n8n_workflow_id}`}
          title="n8n Workflow Editor"
          style={{ width: '100%', height: 'calc(100vh - 180px)', border: '1px solid var(--line)', borderRadius: 22 }}
        />
      ) : null}
    </>
  )
}
