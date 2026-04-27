'use client'

import Link from 'next/link'
import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiRequestError, apiFetch } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName }),
      })
      router.push('/login')
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to register')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Create profile</p>
        <h1>Start a customer inquiry workspace.</h1>
        <p>Registration creates the Supabase auth user and relies on the database trigger for profile rows.</p>

        <form className="form-stack" onSubmit={handleSubmit}>
          {error ? <div className="error-box">{error}</div> : null}
          <div className="field">
            <label htmlFor="fullName">Full name</label>
            <input id="fullName" value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <button className="button" disabled={submitting} type="submit">
            {submitting ? 'Creating...' : 'Create account'}
          </button>
        </form>

        <p>
          Already registered? <Link href="/login">Sign in</Link>
        </p>
      </section>
    </main>
  )
}
