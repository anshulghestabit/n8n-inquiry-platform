'use client'

import Link from 'next/link'
import { FormEvent, useEffect, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'

type Workflow = {
  id: string
  name: string
  description?: string | null
  trigger_channel: string
  status: string
  n8n_workflow_id?: string | null
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  async function loadWorkflows() {
    try {
      const data = await apiFetch<Workflow[]>('/workflows')
      setWorkflows(data)
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to load workflows')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    apiFetch<Workflow[]>('/workflows')
      .then((data) => {
        if (active) {
          setWorkflows(data)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiRequestError ? err.message : 'Unable to load workflows')
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setCreating(true)
    setError('')

    try {
      await apiFetch('/workflows', {
        method: 'POST',
        body: JSON.stringify({
          name: String(formData.get('name') || ''),
          description: String(formData.get('description') || ''),
          trigger_channel: String(formData.get('trigger_channel') || 'gmail'),
        }),
      })
      event.currentTarget.reset()
      await loadWorkflows()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create workflow')
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Layer 7</p>
          <h1>Workflows</h1>
          <p>Create n8n-backed inquiry handlers from the exported 5-agent template.</p>
        </div>
      </header>

      <section className="panel" style={{ marginBottom: '1rem' }}>
        <h2>Create workflow</h2>
        <form className="form-stack" onSubmit={handleCreate}>
          {error ? <div className="error-box">{error}</div> : null}
          <div className="field">
            <label htmlFor="name">Name</label>
            <input id="name" name="name" placeholder="Customer Inquiry Handler" required />
          </div>
          <div className="field">
            <label htmlFor="description">Description</label>
            <input id="description" name="description" placeholder="Handles Gmail inquiries with five agents" />
          </div>
          <div className="field">
            <label htmlFor="trigger_channel">Trigger channel</label>
            <select id="trigger_channel" name="trigger_channel" defaultValue="gmail">
              <option value="gmail">Gmail</option>
              <option value="telegram">Telegram</option>
              <option value="both">Both</option>
            </select>
          </div>
          <button className="button" disabled={creating} type="submit">
            {creating ? 'Creating...' : 'Create workflow'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Existing workflows</h2>
        {loading ? <p className="muted">Loading workflows...</p> : null}
        {!loading && workflows.length === 0 ? <p className="muted">No workflows created yet.</p> : null}
        <div className="list-stack">
          {workflows.map((workflow) => (
            <div className="list-row" key={workflow.id}>
              <div>
                <strong>{workflow.name}</strong>
                <p className="muted">{workflow.trigger_channel} · {workflow.status} · n8n {workflow.n8n_workflow_id || 'pending'}</p>
              </div>
              <div className="row-actions">
                <Link className="button secondary" href={`/workflows/${workflow.id}`}>Open</Link>
                <Link className="button secondary" href={`/workflows/${workflow.id}/agents`}>Agents</Link>
                <Link className="button secondary" href={`/workflows/${workflow.id}/edit`}>Edit</Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
