'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'

type SystemStatus = {
  n8n: boolean
  gmail: boolean
  telegram: boolean
  google_drive: boolean
  google_sheets: boolean
}

const labels: Array<[keyof SystemStatus, string]> = [
  ['n8n', 'n8n'],
  ['gmail', 'Gmail'],
  ['google_sheets', 'Sheets'],
  ['google_drive', 'Drive'],
  ['telegram', 'Telegram'],
]

export function StatusBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true

    async function loadStatus() {
      try {
        const data = await apiFetch<SystemStatus>('/system/status')
        if (active) {
          setStatus(data)
          setError(false)
        }
      } catch {
        if (active) {
          setError(true)
        }
      }
    }

    loadStatus()
    const timer = window.setInterval(loadStatus, 30_000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  return (
    <div className="status-bar">
      {labels.map(([key, label]) => {
        const connected = Boolean(status?.[key]) && !error
        return (
          <span className="status-pill" key={key} title={connected ? 'Connected' : 'Disconnected'}>
            <span className={`dot${connected ? ' ok' : ''}`} />
            {label}
          </span>
        )
      })}
      {error ? <span className="muted">Status unavailable</span> : null}
    </div>
  )
}
