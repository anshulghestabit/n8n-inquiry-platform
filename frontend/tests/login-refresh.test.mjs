import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

/** Source text for the login page under test. */
const loginPage = readFileSync(new URL('../src/app/(auth)/login/page.tsx', import.meta.url), 'utf8')

test('login refreshes auth state after setting the auth cookie', () => {
  assert.match(loginPage, /import\s+\{\s*useAuth\s*\}\s+from\s+['"]@\/lib\/auth-context['"]/)
  assert.match(loginPage, /const\s+\{\s*refreshUser\s*\}\s*=\s*useAuth\(\)/)

  const loginCall = loginPage.indexOf("apiFetch('/auth/login'")
  const refreshCall = loginPage.indexOf('await refreshUser()')
  const navigationCall = loginPage.indexOf("router.push('/dashboard')")

  assert.notEqual(loginCall, -1)
  assert.notEqual(refreshCall, -1)
  assert.notEqual(navigationCall, -1)
  assert.ok(loginCall < refreshCall)
  assert.ok(refreshCall < navigationCall)
})
