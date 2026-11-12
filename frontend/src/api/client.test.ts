import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { apiUrl, type Schemas } from '../test/api'
import { server } from '../test/server'
import { createApiClient } from './client'
import { ApiError, unwrap } from './errors'

const alice: Schemas['CurrentUser'] = {
  id: 1,
  username: 'alice',
  name: 'Alice Johnson',
  is_admin: false,
}

describe('createApiClient', () => {
  it('reads from the same origin and returns the typed body', async () => {
    let requested: string | undefined
    server.use(
      http.get(apiUrl('/api/users/me/'), ({ request }) => {
        requested = request.url
        return HttpResponse.json(alice)
      }),
    )

    const result = await createApiClient().GET('/api/users/me/')

    expect(unwrap(result)).toEqual(alice)
    expect(requested).toBe(`${window.location.origin}/api/users/me/`)
  })

  it('looks up the global fetch when each request is sent, so a later stub is used', async () => {
    const client = createApiClient()
    const stub = vi.fn<(request: Request) => Promise<Response>>(() =>
      Promise.resolve(Response.json(alice)),
    )
    vi.stubGlobal('fetch', stub)
    try {
      await client.GET('/api/users/me/')
    } finally {
      vi.unstubAllGlobals()
    }

    expect(stub).toHaveBeenCalledOnce()
  })

  it('sends every request through the fetch it is given', async () => {
    const send = vi.fn<(request: Request) => Promise<Response>>(() =>
      Promise.resolve(Response.json(alice)),
    )

    await createApiClient({ fetch: send }).GET('/api/users/me/')

    expect(send).toHaveBeenCalledOnce()
    expect(send.mock.calls[0]?.[0].url).toBe(`${window.location.origin}/api/users/me/`)
  })
})

describe('unwrap', () => {
  it('throws an ApiError with the status, the detail and Retry-After', async () => {
    server.use(
      http.get(apiUrl('/api/users/me/'), () =>
        HttpResponse.json({ detail: 'Request was throttled.' } satisfies Schemas['Error'], {
          status: 429,
          headers: { 'Retry-After': '42' },
        }),
      ),
    )

    const result = await createApiClient().GET('/api/users/me/')

    const error = (() => {
      try {
        unwrap(result)
      } catch (caught) {
        return caught
      }
      return undefined
    })()
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 429,
      retryAfter: 42,
      message: 'Request was throttled.',
      body: { detail: 'Request was throttled.' },
    })
  })

  it('keeps field errors as the body and has no Retry-After without the header', async () => {
    const fieldErrors = { title: ['This field is required.'] }
    server.use(
      http.post(apiUrl('/api/tasks/'), () => HttpResponse.json(fieldErrors, { status: 400 })),
    )

    const result = await createApiClient().POST('/api/tasks/', { body: { title: '' } })

    expect(() => unwrap(result)).toThrow(
      expect.objectContaining({ status: 400, body: fieldErrors, retryAfter: null }),
    )
  })
})

describe('query parameters', () => {
  const emptyPage: Schemas['PaginatedTaskList'] = {
    count: 0,
    next: null,
    previous: null,
    results: [],
  }

  async function listTasks(query: {
    ordering?: ('status' | '-due_date' | 'created_at')[]
    status?: ('to_do' | 'in_progress' | 'done')[]
  }): Promise<URLSearchParams> {
    let url: URL | undefined
    server.use(
      http.get(apiUrl('/api/tasks/'), ({ request }) => {
        url = new URL(request.url)
        return HttpResponse.json(emptyPage)
      }),
    )
    await createApiClient().GET('/api/tasks/', { params: { query } })
    if (!url) throw new Error('the request never reached the API')
    return url.searchParams
  }

  it('sends ordering as one comma-separated parameter, as the schema declares', async () => {
    const params = await listTasks({ ordering: ['status', '-due_date'] })

    expect(params.getAll('ordering')).toEqual(['status,-due_date'])
  })

  it('repeats status once per value, as the schema declares', async () => {
    const params = await listTasks({ status: ['to_do', 'done'] })

    expect(params.getAll('status')).toEqual(['to_do', 'done'])
  })

  it('serializes both styles in one request', async () => {
    const params = await listTasks({ ordering: ['created_at'], status: ['in_progress'] })

    expect(params.getAll('ordering')).toEqual(['created_at'])
    expect(params.getAll('status')).toEqual(['in_progress'])
  })
})
