import { act, waitFor } from '@testing-library/react'
import { HttpResponse, type JsonBodyType } from 'msw'
import { describe, expect, it } from 'vitest'
import { useAuth } from '../../../auth/useAuth'
import { logoutSucceeds, refreshAnswers } from '../../../test/handlers'
import { createTestQueryClient } from '../../../test/queryClient'
import { renderRoute } from '../../../test/render'
import { server } from '../../../test/server'
import { aPage, aTask, held, updateTask } from '../../../test/tasks'
import { taskKeys } from './keys'
import { useUpdateTask } from './useTaskMutations'

// What a change does to the cached data (ADR 0018), seen in the query cache itself. The page
// tests see only what the screen shows, which a refetch could provide on its own.

const invoice = aTask({ id: 7, title: 'Send the October invoice' })
const renamed = { ...invoice, title: 'Send the November invoice' }
const detailKey = taskKeys.detail(7)
const listKey = taskKeys.list({ page_size: 20 })

async function renderUpdate({ cached = true } = {}) {
  server.use(refreshAnswers('alice-token').handler)
  const queryClient = createTestQueryClient()
  if (cached) queryClient.setQueryData(detailKey, invoice)
  queryClient.setQueryData(listKey, aPage([invoice]))
  const seen: { latest: ReturnType<typeof useUpdateTask> | null; status: string } = {
    latest: null,
    status: '',
  }
  function Probe() {
    seen.latest = useUpdateTask(7)
    seen.status = useAuth().status
    return null
  }
  const app = renderRoute(<Probe />, { queryClient })
  await waitFor(() => {
    expect(seen.status).toBe('authenticated')
  })
  const update = () => {
    if (seen.latest === null) throw new Error('the hook never rendered')
    return seen.latest
  }
  // Settles the mutation either way: these tests look at the cache, not the result.
  const save = (title: string) =>
    update()
      .mutateAsync({ title })
      .catch(() => undefined)
  return { ...app, queryClient, save }
}

function answer(status: number, body: JsonBodyType) {
  return () => HttpResponse.json(body, { status })
}

describe('after a save', () => {
  it('the cached task is the one the API returned, and every list is stale', async () => {
    server.use(updateTask(renamed).handler)
    const { queryClient, save } = await renderUpdate()

    await act(() => save('Send the November invoice'))

    expect(queryClient.getQueryData(detailKey)).toEqual(renamed)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it("a task that wasn't cached isn't cached by the answer", async () => {
    server.use(updateTask(renamed).handler)
    const { queryClient, save } = await renderUpdate({ cached: false })

    await act(() => save('Send the November invoice'))

    expect(queryClient.getQueryData(detailKey)).toBeUndefined()
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('an answer that arrives after logout leaves the cleared cache empty', async () => {
    const response = held()
    server.use(
      logoutSucceeds(),
      updateTask(async () => {
        await response.wait
        return HttpResponse.json(renamed)
      }).handler,
    )
    const { auth, queryClient, save } = await renderUpdate()

    const saving = save('Send the November invoice')
    await act(() => auth.session.logout())
    expect(queryClient.getQueryData(detailKey)).toBeUndefined()
    response.release()
    await act(() => saving)

    // The previous user's task must not come back into the next user's cache (ADR 0016).
    expect(queryClient.getQueryCache().findAll({ queryKey: taskKeys.all })).toEqual([])
  })
})

describe('after a refusal', () => {
  it('a 404 drops the cached task and marks every list stale', async () => {
    server.use(updateTask(answer(404, { detail: 'Not found.' })).handler)
    const { queryClient, save } = await renderUpdate()

    await act(() => save('Send the November invoice'))

    expect(queryClient.getQueryData(detailKey)).toBeUndefined()
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('a 403 keeps the task until it refetches, and marks it and every list stale', async () => {
    server.use(updateTask(answer(403, { detail: 'Not allowed.' })).handler)
    const { queryClient, save } = await renderUpdate()

    await act(() => save('Send the November invoice'))

    expect(queryClient.getQueryData(detailKey)).toEqual(invoice)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('a 400 changes nothing in the cache: the task is as it was', async () => {
    server.use(updateTask(answer(400, { title: ['Must be 1 to 200 characters.'] })).handler)
    const { queryClient, save } = await renderUpdate()

    await act(() => save(''))

    expect(queryClient.getQueryData(detailKey)).toEqual(invoice)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(false)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(false)
  })
})
