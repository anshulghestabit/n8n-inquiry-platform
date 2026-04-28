'use client'

import { useEffect, useMemo, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'

type SourceType = 'gmail' | 'telegram' | 'google_drive' | 'google_sheets'

type Integration = {
  source_type: SourceType
  is_connected: boolean
  last_verified_at?: string | null
}

const labels: Record<SourceType, { name: string; description: string }> = {
  gmail: { name: 'Gmail', description: 'Verifies an attached n8n Gmail OAuth credential for replies and triggers.' },
  google_sheets: { name: 'Google Sheets', description: 'Verifies an attached n8n Sheets credential and configured sheet id.' },
  google_drive: { name: 'Google Drive', description: 'Verifies an attached n8n Drive OAuth credential for KB retrieval.' },
  telegram: { name: 'Telegram', description: 'Verifies the Telegram bot token and attached n8n Telegram credential.' },
}

const actionVerb: Record<'connect' | 'verify' | 'disconnect', string> = {
  connect: 'connected',
  verify: 'verified',
  disconnect: 'disconnected',
}

export default function IntegrationsPage() {
  const [items, setItems] = useState<Integration[]>([])
  const [credentialHint, setCredentialHint] = useState<Record<SourceType, string>>({
    gmail: '',
    telegram: '',
    google_drive: '',
    google_sheets: '',
  })
  const [busy, setBusy] = useState<Record<SourceType, boolean>>({
    gmail: false,
    telegram: false,
    google_drive: false,
    google_sheets: false,
  })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const integrationMap = useMemo(() => {
    return items.reduce<Record<SourceType, Integration>>((acc, item) => {
      acc[item.source_type] = item
      return acc
    }, {} as Record<SourceType, Integration>)
  }, [items])

  async function loadIntegrations() {
    const data = await apiFetch<Integration[]>('/system/integrations')
    setItems(data)
  }

  useEffect(() => {
    let active = true

    apiFetch<Integration[]>('/system/integrations')
      .then((data) => {
        if (active) {
          setItems(data)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiRequestError ? err.message : 'Unable to load integrations')
        }
      })

    return () => {
      active = false
    }
  }, [])

  async function runAction(sourceType: SourceType, action: 'connect' | 'verify' | 'disconnect') {
    setError('')
    setMessage('')
    setBusy((prev) => ({ ...prev, [sourceType]: true }))

    try {
      const body = action === 'disconnect' ? undefined : JSON.stringify({ credential_hint: credentialHint[sourceType] })
      await apiFetch(`/system/integrations/${sourceType}/${action}`, {
        method: 'POST',
        body,
      })
      await loadIntegrations()
      setMessage(`${labels[sourceType].name} ${actionVerb[action]} successfully`)
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : `Unable to ${action} ${labels[sourceType].name}`)
    } finally {
      setBusy((prev) => ({ ...prev, [sourceType]: false }))
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Layer 6.5</p>
          <h1>Integrations</h1>
          <p>Connect only after the backend validates the live n8n credential references used by workflow execution.</p>
        </div>
      </header>

      {error ? <div className="error-box" style={{ marginBottom: '1rem' }}>{error}</div> : null}
      {message ? <div className="status-pill" style={{ marginBottom: '1rem' }}><span className="dot ok" />{message}</div> : null}

      <section className="grid">
        {(Object.keys(labels) as SourceType[]).map((sourceType) => {
          const item = integrationMap[sourceType]
          const connected = Boolean(item?.is_connected)
          const verifiedAt = item?.last_verified_at
          return (
            <article className="panel" key={sourceType}>
              <h2>{labels[sourceType].name}</h2>
              <p className="muted">{labels[sourceType].description}</p>
              <p className="muted" style={{ marginTop: '0.35rem' }}>
                Status: {connected ? 'Connected' : 'Disconnected'}
                {verifiedAt ? ` · Verified ${new Date(verifiedAt).toLocaleString()}` : ''}
              </p>
              <div className="field" style={{ marginTop: '0.75rem' }}>
                <label htmlFor={`${sourceType}_hint`}>Credential hint</label>
                <input
                  id={`${sourceType}_hint`}
                  name={`${sourceType}_hint`}
                  onChange={(event) =>
                    setCredentialHint((prev) => ({
                      ...prev,
                      [sourceType]: event.target.value,
                    }))
                  }
                  placeholder="Operator note or credential reference"
                  value={credentialHint[sourceType]}
                />
              </div>
              <div className="row-actions">
                <button className="button" disabled={busy[sourceType]} onClick={() => runAction(sourceType, 'connect')} type="button">
                  Connect
                </button>
                <button className="button secondary" disabled={busy[sourceType] || !connected} onClick={() => runAction(sourceType, 'verify')} type="button">
                  Verify
                </button>
                <button className="button secondary" disabled={busy[sourceType] || !connected} onClick={() => runAction(sourceType, 'disconnect')} type="button">
                  Disconnect
                </button>
              </div>
            </article>
          )
        })}
      </section>
    </>
  )
}
