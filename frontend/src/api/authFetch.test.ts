import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { createAuth } from '../auth/createAuth'
import { apiUrl, type Schemas } from '../test/api'
import { loginSucceeds, logoutSucceeds, refreshAnswers } from '../test/handlers'
import { server } from '../test/server'

const alice: Schemas['CurrentUser'] = {
  id: 1,
  username: 'alice',
  name: 'Alice Johnson',
  is_admin: false,
}

async function signedIn(access = 'access-1') {
  server.use(loginSucceeds(access))
  const auth = createAuth()
  await auth.session.login({ username: 'alice', password: 'demo-password' })
  return auth
}

/** /api/users/me/ answering 200 only to `Bearer <valid>`, 401 otherwise. Records each header. */
function meAcceptingOnly(valid: string) {
  const seen: (string | null)[] = []
  server.use(
    http.get(apiUrl('/api/users/me/'), ({ request }) => {
      const header = request.headers.get('Authorization')
      seen.push(header)
      if (header === `Bearer ${valid}`) return HttpResponse.json(alice)
      return HttpResponse.json({ detail: 'Token is expired' } satisfies Schemas['Error'], {
        status: 401,
      })
    }),
  )
  return seen
}

describe('the access token', () => {
  it('is added as each request is sent, so a rotated token is used next time', async () => {
    const { api, session } = await signedIn('access-1')
    const seen: (string | null)[] = []
    server.use(
      http.get(apiUrl('/api/users/me/'), ({ request }) => {
        seen.push(request.headers.get('Authorization'))
        return HttpResponse.json(alice)
      }),
      refreshAnswers('access-2').handler,
    )

    await api.GET('/api/users/me/')
    await session.refresh()
    await api.GET('/api/users/me/')

    expect(seen).toEqual(['Bearer access-1', 'Bearer access-2'])
  })

  it('is left out when there is none', async () => {
    const { api } = createAuth()
    let header: string | null = 'not checked'
    server.use(
      http.get(apiUrl('/api/users/me/'), ({ request }) => {
        header = request.headers.get('Authorization')
        return HttpResponse.json(alice)
      }),
    )

    await api.GET('/api/users/me/')

    expect(header).toBeNull()
  })

  it('is never sent to /api/auth/, whose 401 is not retried', async () => {
    const { api } = await signedIn()
    let calls = 0
    let header: string | null = 'not checked'
    server.use(
      http.post(apiUrl('/api/auth/token/refresh/'), ({ request }) => {
        calls += 1
        header = request.headers.get('Authorization')
        return HttpResponse.json({ detail: 'Token is invalid' }, { status: 401 })
      }),
    )

    const { response } = await api.POST('/api/auth/token/refresh/')

    expect(response.status).toBe(401)
    expect(calls).toBe(1)
    expect(header).toBeNull()
  })
})

describe('a 401', () => {
  it('leads to one refresh and one retry with the new token, body included', async () => {
    const { api } = await signedIn('access-1')
    const refresh = refreshAnswers('access-2')
    const bodies: unknown[] = []
    server.use(
      refresh.handler,
      http.post(apiUrl('/api/tasks/'), async ({ request }) => {
        bodies.push(await request.json())
        if (request.headers.get('Authorization') !== 'Bearer access-2') {
          return HttpResponse.json({ detail: 'Token is expired' }, { status: 401 })
        }
        return HttpResponse.json({ id: 7 }, { status: 201 })
      }),
    )

    const { response } = await api.POST('/api/tasks/', { body: { title: 'Write the tests' } })

    expect(response.status).toBe(201)
    expect(refresh.count()).toBe(1)
    expect(bodies).toEqual([{ title: 'Write the tests' }, { title: 'Write the tests' }])
  })

  it('on five requests at once leads to exactly one refresh, and all five succeed', async () => {
    const { api } = await signedIn('access-1')
    const seen = meAcceptingOnly('access-2')
    const refresh = refreshAnswers('access-2')
    server.use(refresh.handler)

    const results = await Promise.all(Array.from({ length: 5 }, () => api.GET('/api/users/me/')))

    expect(results.map((result) => result.data)).toEqual(Array(5).fill(alice))
    expect(refresh.count()).toBe(1)
    expect(seen.filter((header) => header === 'Bearer access-1')).toHaveLength(5)
  })

  it('for a token already replaced is retried with the new one, without a refresh', async () => {
    const { api, session } = await signedIn('access-1')
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.get(apiUrl('/api/users/me/'), async ({ request }) => {
        if (request.headers.get('Authorization') === 'Bearer access-2') {
          return HttpResponse.json(alice)
        }
        await held
        return HttpResponse.json({ detail: 'Token is expired' }, { status: 401 })
      }),
    )
    const refresh = refreshAnswers('access-2')
    server.use(refresh.handler)

    const pending = api.GET('/api/users/me/')
    await session.refresh()
    release()
    const { data } = await pending

    expect(data).toEqual(alice)
    expect(refresh.count()).toBe(1)
  })

  it('after the retry is returned as is, with no second refresh', async () => {
    const { api } = await signedIn('access-1')
    meAcceptingOnly('nothing')
    const refresh = refreshAnswers('access-2', 'access-3')
    server.use(refresh.handler)

    const { response } = await api.GET('/api/users/me/')

    expect(response.status).toBe(401)
    expect(refresh.count()).toBe(1)
  })

  it('whose refresh is rejected is returned, and the session is signed out', async () => {
    const { api, session } = await signedIn('access-1')
    const seen = meAcceptingOnly('nothing')
    server.use(refreshAnswers(401, 401).handler)

    const { response } = await api.GET('/api/users/me/')

    expect(response.status).toBe(401)
    expect(seen).toHaveLength(1)
    expect(session.getState()).toEqual({ status: 'anonymous' })
  })

  it('whose refresh is unavailable is returned, and the session is kept', async () => {
    const { api, session } = await signedIn('access-1')
    const seen = meAcceptingOnly('nothing')
    server.use(refreshAnswers(503).handler)

    const { response } = await api.GET('/api/users/me/')

    expect(response.status).toBe(401)
    expect(seen).toHaveLength(1)
    expect(session.getState()).toEqual({ status: 'authenticated' })
    expect(session.getAccessToken()).toBe('access-1')
  })

  it('for a request sent before logout does not refresh', async () => {
    const { api, session } = await signedIn('access-1')
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.get(apiUrl('/api/users/me/'), async () => {
        await held
        return HttpResponse.json({ detail: 'Token is expired' }, { status: 401 })
      }),
      logoutSucceeds(),
    )
    const refresh = refreshAnswers('access-2')
    server.use(refresh.handler)

    const pending = api.GET('/api/users/me/')
    await session.logout()
    release()
    const { response } = await pending

    expect(response.status).toBe(401)
    expect(refresh.count()).toBe(0)
    expect(session.getAccessToken()).toBeNull()
  })
})

describe('an AbortSignal', () => {
  it('reaches fetch, so a cancelled query stops its request', async () => {
    const { api } = await signedIn()
    server.use(http.get(apiUrl('/api/users/me/'), () => HttpResponse.json(alice)))
    const controller = new AbortController()
    controller.abort()

    await expect(api.GET('/api/users/me/', { signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    })
  })
})
