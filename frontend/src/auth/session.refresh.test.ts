import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { createApiClient } from '../api/client'
import { apiUrl } from '../test/api'
import { loginSucceeds, logoutSucceeds, refreshAnswers } from '../test/handlers'
import { server } from '../test/server'
import { createSession } from './session'

function newSession() {
  return createSession({ authClient: createApiClient() })
}

async function signedIn() {
  server.use(loginSucceeds('access-1'))
  const session = newSession()
  await session.login({ username: 'alice', password: 'demo-password' })
  return session
}

/** A refresh handler that holds its 200 until release() is called, then calls onAnswer. */
function heldRefresh(access: string, onAnswer: () => void = () => undefined) {
  let release: () => void = () => undefined
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  server.use(
    http.post(apiUrl('/api/auth/token/refresh/'), async () => {
      await held
      onAnswer()
      return HttpResponse.json({ access })
    }),
  )
  return () => {
    release()
  }
}

describe('restore', () => {
  it('sends one refresh even when called twice, as StrictMode does', async () => {
    const refresh = refreshAnswers('access-1')
    server.use(refresh.handler)
    const session = newSession()

    const first = session.restore()
    const second = session.restore()
    const outcomes = await Promise.all([first, second])

    expect(second).toBe(first)
    expect(outcomes).toEqual(['refreshed', 'refreshed'])
    await session.restore()
    expect(refresh.count()).toBe(1)
  })

  it('becomes authenticated with the new token when the cookie is good', async () => {
    server.use(refreshAnswers('access-1').handler)
    const session = newSession()

    expect(await session.restore()).toBe('refreshed')
    expect(session.getState()).toEqual({ status: 'authenticated' })
    expect(session.getAccessToken()).toBe('access-1')
  })

  it('becomes anonymous without a cookie (204)', async () => {
    server.use(refreshAnswers(204).handler)
    const session = newSession()

    expect(await session.restore()).toBe('rejected')
    expect(session.getState()).toEqual({ status: 'anonymous' })
    expect(session.getAccessToken()).toBeNull()
  })

  it('becomes anonymous when the cookie is refused twice (401, 401)', async () => {
    const refresh = refreshAnswers(401, 401)
    server.use(refresh.handler)
    const session = newSession()

    expect(await session.restore()).toBe('rejected')
    expect(session.getState()).toEqual({ status: 'anonymous' })
    expect(refresh.count()).toBe(2)
  })

  it.each([['unreachable'], [500], [429]])(
    'is unavailable, not anonymous, when the backend can not answer (%s)',
    async (answer) => {
      server.use(refreshAnswers(answer).handler)
      const session = newSession()

      expect(await session.restore()).toBe('unavailable')
      expect(session.getState()).toEqual({ status: 'unavailable' })
    },
  )

  it('can be retried after unavailable, restoring meanwhile', async () => {
    server.use(refreshAnswers('unreachable').handler)
    const session = newSession()
    await session.restore()
    const release = heldRefresh('access-2')

    const retry = session.retryRestore()
    expect(session.getState()).toEqual({ status: 'restoring' })
    release()

    expect(await retry).toBe('refreshed')
    expect(session.getState()).toEqual({ status: 'authenticated' })
    expect(session.getAccessToken()).toBe('access-2')
  })
})

describe('refresh', () => {
  it('sends one request for three concurrent callers, who share the result', async () => {
    const session = await signedIn()
    const refresh = refreshAnswers('access-2')
    server.use(refresh.handler)

    const outcomes = await Promise.all([session.refresh(), session.refresh(), session.refresh()])

    expect(outcomes).toEqual(['refreshed', 'refreshed', 'refreshed'])
    expect(refresh.count()).toBe(1)
    expect(session.getAccessToken()).toBe('access-2')
  })

  it('sends a new request once the previous one has answered', async () => {
    const session = await signedIn()
    const refresh = refreshAnswers('access-2', 'access-3')
    server.use(refresh.handler)

    await session.refresh()
    await session.refresh()

    expect(refresh.count()).toBe(2)
    expect(session.getAccessToken()).toBe('access-3')
  })

  it('retries once after a 401, because another tab may have rotated the cookie', async () => {
    const session = await signedIn()
    const refresh = refreshAnswers(401, 'access-2')
    server.use(refresh.handler)

    expect(await session.refresh()).toBe('refreshed')
    expect(refresh.count()).toBe(2)
    expect(session.getAccessToken()).toBe('access-2')
  })

  it('signs out when the cookie is refused twice', async () => {
    const session = await signedIn()
    const refresh = refreshAnswers(401, 401, 'never sent')
    server.use(refresh.handler)

    expect(await session.refresh()).toBe('rejected')
    expect(refresh.count()).toBe(2)
    expect(session.getAccessToken()).toBeNull()
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })

  it('signs out when there is no cookie any more (204)', async () => {
    const session = await signedIn()
    server.use(refreshAnswers(204).handler)

    expect(await session.refresh()).toBe('rejected')
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })

  it('keeps the session when the backend can not answer', async () => {
    const session = await signedIn()
    server.use(refreshAnswers(503).handler)

    expect(await session.refresh()).toBe('unavailable')
    expect(session.getState()).toEqual({ status: 'authenticated' })
    expect(session.getAccessToken()).toBe('access-1')
  })
})

describe('logout while a refresh is in flight', () => {
  it('waits for the refresh, so it revokes the newest cookie', async () => {
    const session = await signedIn()
    const events: string[] = []
    const release = heldRefresh('access-2', () => events.push('refresh answered'))
    server.use(
      http.post(apiUrl('/api/auth/logout/'), () => {
        events.push('logout')
        return new HttpResponse(null, { status: 204 })
      }),
    )

    const refresh = session.refresh()
    const logout = session.logout()
    release()
    await logout

    expect(await refresh).toBe('rejected')
    expect(events).toEqual(['refresh answered', 'logout'])
  })

  it('does not let the refresh bring the token back', async () => {
    const session = await signedIn()
    const release = heldRefresh('access-2')
    server.use(logoutSucceeds())

    const refresh = session.refresh()
    const logout = session.logout()
    release()
    await logout

    expect(await refresh).toBe('rejected')
    expect(session.getAccessToken()).toBeNull()
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })
})

describe('refresh while a logout is in progress', () => {
  // Codex review of #48: a refresh that starts after logout has bumped the generation passes
  // the stale check, so it must not be sent at all.
  function heldLogout() {
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.post(apiUrl('/api/auth/logout/'), async () => {
        await held
        return new HttpResponse(null, { status: 204 })
      }),
    )
    return () => {
      release()
    }
  }

  it('sends no refresh request, and the token stays gone', async () => {
    const session = await signedIn()
    const refresh = refreshAnswers('access-2')
    server.use(refresh.handler)
    const release = heldLogout()

    const logout = session.logout()
    const outcome = await session.refresh()
    release()
    await logout

    expect(outcome).toBe('rejected')
    expect(refresh.count()).toBe(0)
    expect(session.getAccessToken()).toBeNull()
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })

  it('refreshes again once the logout has finished', async () => {
    const session = await signedIn()
    server.use(logoutSucceeds())
    await session.logout()
    const refresh = refreshAnswers(204)
    server.use(refresh.handler)

    expect(await session.refresh()).toBe('rejected')
    expect(refresh.count()).toBe(1)
  })
})
