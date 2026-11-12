import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../api/client'
import { apiUrl } from '../test/api'
import {
  loginFails,
  loginSucceeds,
  loginUnreachable,
  logoutSucceeds,
  logoutUnreachable,
} from '../test/handlers'
import { server } from '../test/server'
import { createSession, LoginError } from './session'

const credentials = { username: 'alice', password: 'demo-password' }

function newSession() {
  return createSession({ authClient: createApiClient() })
}

async function loginError(promise: Promise<void>): Promise<LoginError> {
  try {
    await promise
  } catch (error) {
    if (error instanceof LoginError) return error
    throw error
  }
  throw new Error('the login succeeded')
}

describe('a new session', () => {
  it('is restoring, not anonymous, and has no token', () => {
    const session = newSession()

    expect(session.getState()).toEqual({ status: 'restoring' })
    expect(session.getAccessToken()).toBeNull()
  })
})

describe('login', () => {
  it('posts the credentials as JSON to /api/auth/token/', async () => {
    let body: unknown
    server.use(
      http.post(apiUrl('/api/auth/token/'), async ({ request }) => {
        body = await request.json()
        return HttpResponse.json({ access: 'access-1' })
      }),
    )

    await newSession().login(credentials)

    expect(body).toEqual(credentials)
  })

  it('keeps the access token in memory and becomes authenticated', async () => {
    server.use(loginSucceeds('access-1'))
    const session = newSession()
    const listener = vi.fn()
    session.subscribe(listener)

    await session.login(credentials)

    expect(session.getAccessToken()).toBe('access-1')
    expect(session.getState()).toEqual({ status: 'authenticated' })
    expect(listener).toHaveBeenCalledOnce()
  })

  it('writes nothing to localStorage, sessionStorage or document.cookie', async () => {
    server.use(loginSucceeds('access-1'))
    const setItem = vi.spyOn(Storage.prototype, 'setItem')

    await newSession().login(credentials)

    expect(setItem).not.toHaveBeenCalled()
    expect(localStorage).toHaveLength(0)
    expect(sessionStorage).toHaveLength(0)
    expect(document.cookie).toBe('')
    setItem.mockRestore()
  })

  it('reports wrong credentials (401) as invalid and stays signed out', async () => {
    server.use(loginFails(401))
    const session = newSession()

    const error = await loginError(session.login(credentials))

    expect(error.kind).toBe('invalid')
    expect(session.getAccessToken()).toBeNull()
    expect(session.getState().status).not.toBe('authenticated')
  })

  it('reports a throttled login (429) with the seconds from Retry-After', async () => {
    server.use(loginFails(429, { 'Retry-After': '42' }))

    const error = await loginError(newSession().login(credentials))

    expect(error).toMatchObject({ kind: 'throttled', retryAfter: 42 })
  })

  it('reports a server that is down as unavailable', async () => {
    server.use(loginUnreachable())

    const error = await loginError(newSession().login(credentials))

    expect(error).toMatchObject({ kind: 'unavailable', retryAfter: null })
  })

  it('reports a server error (500) as unavailable', async () => {
    server.use(loginFails(500))

    const error = await loginError(newSession().login(credentials))

    expect(error.kind).toBe('unavailable')
  })
})

describe('logout', () => {
  async function signedIn() {
    server.use(loginSucceeds('access-1'))
    const session = newSession()
    await session.login(credentials)
    return session
  }

  it('posts to /api/auth/logout/, drops the token and becomes anonymous', async () => {
    const session = await signedIn()
    let loggedOut = false
    server.use(
      http.post(apiUrl('/api/auth/logout/'), () => {
        loggedOut = true
        return new HttpResponse(null, { status: 204 })
      }),
    )

    await session.logout()

    expect(loggedOut).toBe(true)
    expect(session.getAccessToken()).toBeNull()
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })

  it('drops the token before the backend answers', async () => {
    const session = await signedIn()
    let tokenWhileLoggingOut: string | null = 'not checked'
    server.use(
      http.post(apiUrl('/api/auth/logout/'), () => {
        tokenWhileLoggingOut = session.getAccessToken()
        return new HttpResponse(null, { status: 204 })
      }),
    )

    await session.logout()

    expect(tokenWhileLoggingOut).toBeNull()
  })

  it('changes the generation, so work started before the logout can tell', async () => {
    const session = await signedIn()
    server.use(logoutSucceeds())
    const before = session.generation()

    await session.logout()

    expect(session.generation()).not.toBe(before)
  })

  it('still signs out locally when the backend is unreachable', async () => {
    const session = await signedIn()
    server.use(logoutUnreachable())

    await session.logout()

    expect(session.getAccessToken()).toBeNull()
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })
})

describe('subscribe', () => {
  it('notifies on each status change until unsubscribed, with a stable state object', async () => {
    server.use(loginSucceeds(), logoutSucceeds())
    const session = newSession()
    const listener = vi.fn()
    const unsubscribe = session.subscribe(listener)
    const first = session.getState()

    expect(session.getState()).toBe(first)
    await session.login(credentials)
    expect(listener).toHaveBeenCalledTimes(1)
    unsubscribe()
    await session.logout()

    expect(listener).toHaveBeenCalledTimes(1)
    expect(session.getState()).not.toBe(first)
  })
})
