'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch } from './api'

export type UserProfile = {
  id: string
  email: string
  full_name?: string | null
  avatar_url?: string | null
}

type AuthContextValue = {
  user: UserProfile | null
  loading: boolean
  refreshUser: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  async function refreshUser() {
    try {
      const profile = await apiFetch<UserProfile>('/auth/me')
      setUser(profile)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  async function logout() {
    try {
      await apiFetch<{ message: string }>('/auth/logout', { method: 'POST' })
    } finally {
      setUser(null)
      setLoading(false)
      window.location.href = '/login'
    }
  }

  useEffect(() => {
    let active = true

    apiFetch<UserProfile>('/auth/me')
      .then((profile) => {
        if (active) {
          setUser(profile)
        }
      })
      .catch(() => {
        if (active) {
          setUser(null)
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

  return (
    <AuthContext.Provider value={{ user, loading, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
