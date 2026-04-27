'use client'

import { FormEvent, useState } from 'react'
import { ApiRequestError, apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const fullName = String(formData.get('fullName') || '')
    const avatarUrl = String(formData.get('avatarUrl') || '')
    setSubmitting(true)
    setMessage('')
    setError('')

    try {
      await apiFetch('/auth/me', {
        method: 'PUT',
        body: JSON.stringify({ full_name: fullName, avatar_url: avatarUrl || null }),
      })
      await refreshUser()
      setMessage('Profile updated')
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to update profile')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Profile</h1>
          <p>Update the profile record created by the Supabase signup trigger.</p>
        </div>
      </header>

      <section className="panel" style={{ maxWidth: 680 }}>
        <form className="form-stack" key={user?.id || 'loading'} onSubmit={handleSubmit}>
          {message ? <div className="status-pill"><span className="dot ok" />{message}</div> : null}
          {error ? <div className="error-box">{error}</div> : null}
          <div className="field">
            <label>Email</label>
            <input value={user?.email || ''} disabled />
          </div>
          <div className="field">
            <label htmlFor="fullName">Full name</label>
            <input id="fullName" name="fullName" defaultValue={user?.full_name || ''} />
          </div>
          <div className="field">
            <label htmlFor="avatarUrl">Avatar URL</label>
            <input id="avatarUrl" name="avatarUrl" defaultValue={user?.avatar_url || ''} />
          </div>
          <button className="button" disabled={submitting} type="submit">
            {submitting ? 'Saving...' : 'Save profile'}
          </button>
        </form>
      </section>
    </>
  )
}
