'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { ApiRequestError, apiFetch } from '@/lib/api'

type Agent = {
  id: string
  name: string
  role: string
  system_prompt: string
  order_index: number
}

export default function WorkflowAgentsPage() {
  const params = useParams<{ id: string }>()
  const [agents, setAgents] = useState<Agent[]>([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function loadAgents() {
    try {
      const data = await apiFetch<Agent[]>(`/workflows/${params.id}/agents`)
      setAgents(data)
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to load agents')
    }
  }

  useEffect(() => {
    let active = true
    apiFetch<Agent[]>(`/workflows/${params.id}/agents`)
      .then((data) => {
        if (active) {
          setAgents(data)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiRequestError ? err.message : 'Unable to load agents')
        }
      })

    return () => {
      active = false
    }
  }, [params.id])

  async function handleSave(event: FormEvent<HTMLFormElement>, agentId: string) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setMessage('')
    setError('')

    try {
      await apiFetch(`/agents/${agentId}`, {
        method: 'PUT',
        body: JSON.stringify({ system_prompt: String(formData.get('system_prompt') || '') }),
      })
      setMessage('Agent prompt synced to n8n')
      await loadAgents()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to save agent')
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Agent configuration</p>
          <h1>Five-agent chain</h1>
          <p>Saving a prompt updates Supabase and the matching n8n node.</p>
        </div>
      </header>

      {message ? <div className="status-pill" style={{ marginBottom: '1rem' }}><span className="dot ok" />{message}</div> : null}
      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}

      <section className="list-stack">
        {agents.map((agent) => (
          <article className="panel" key={agent.id}>
            <h2>{agent.order_index}. {agent.name}</h2>
            <p className="muted">Role: {agent.role}</p>
            <form className="form-stack" onSubmit={(event) => handleSave(event, agent.id)}>
              <div className="field">
                <label htmlFor={`prompt-${agent.id}`}>System prompt</label>
                <textarea id={`prompt-${agent.id}`} name="system_prompt" defaultValue={agent.system_prompt} rows={5} required />
              </div>
              <button className="button" type="submit">Save prompt</button>
            </form>
          </article>
        ))}
      </section>
    </>
  )
}
