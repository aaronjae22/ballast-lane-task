import { act, waitFor } from '@testing-library/react'
import { HttpResponse, type JsonBodyType } from 'msw'
import { describe, expect, it } from 'vitest'
import { useAuth } from '../../../auth/useAuth'
import { logoutSucceeds, refreshAnswers, users } from '../../../test/handlers'
import { createTestQueryClient } from '../../../test/queryClient'
import { renderRoute } from '../../../test/render'
import { server } from '../../../test/server'
import {
  aPage,
  aTask,
  assignTask,
  changeStatus,
  held,
  summaryOf,
  updateTask,
} from '../../../test/tasks'
import type { Transition } from '../permissions'
import { taskKeys } from './keys'
import { useAssignTask, useTaskTransition, useUpdateTask } from './useTaskMutations'

// What a change does to the cached data (ADR 0018), seen in the query cache itself. The page
// tests see only what the screen shows, which a refetch could provide on its own.

const invoice = aTask({ id: 7, title: 'Send the October invoice' })
const renamed = { ...invoice, title: 'Send the November invoice' }
const detailKey = taskKeys.detail(7)
const listKey = taskKeys.list({ page_size: 20 })

// Renders a mutation hook for a signed-in user, with task 7 in the cache (unless `cached` is
// false) and one list, and returns the hook's latest result.
async function renderMutation<Result>(useHook: () => Result, { cached = true } = {}) {
  server.use(refreshAnswers('alice-token').handler)
  const queryClient = createTestQueryClient()
  if (cached) queryClient.setQueryData(detailKey, invoice)
  queryClient.setQueryData(listKey, aPage([invoice]))
  const seen: { latest: Result | null; status: string } = { latest: null, status: '' }
  function Probe() {
    seen.latest = useHook()
    seen.status = useAuth().status
    return null
  }
  const app = renderRoute(<Probe />, { queryClient })
  await waitFor(() => {
    expect(seen.status).toBe('authenticated')
  })
  const result = () => {
    if (seen.latest === null) throw new Error('the hook never rendered')
    return seen.latest
  }
  return { ...app, queryClient, result }
}

// Each mutation settles either way: these tests look at the cache, not the result.
async function renderUpdate(options: { cached?: boolean } = {}) {
  const app = await renderMutation(() => useUpdateTask(7), options)
  const save = (title: string) =>
    app
      .result()
      .mutateAsync({ title })
      .catch(() => undefined)
  return { ...app, save }
}

async function renderTransition() {
  const app = await renderMutation(() => useTaskTransition(7))
  const change = (transition: Transition) =>
    app
      .result()
      .mutateAsync(transition)
      .catch(() => undefined)
  return { ...app, change }
}

async function renderAssign() {
  const app = await renderMutation(() => useAssignTask(7))
  const assign = (assigneeId: number | null) =>
    app
      .result()
      .mutateAsync(assigneeId)
      .catch(() => undefined)
  return { ...app, assign }
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

describe('a status change', () => {
  it.each([
    ['start', { status: 'in_progress' }],
    ['complete', { status: 'done', completed_at: '2026-11-12T17:05:00Z' }],
    ['reopen', { status: 'to_do' }],
  ] as const)('%s asks for it, then caches the task it returns', async (transition, change) => {
    const changed = { ...invoice, ...change }
    const status = changeStatus(changed)
    server.use(...status.handlers)
    const { queryClient, change: send } = await renderTransition()

    await act(() => send(transition))

    expect(status.calls()).toEqual([`7/${transition}`])
    expect(queryClient.getQueryData(detailKey)).toEqual(changed)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('a 409 keeps the task until it refetches, and marks it and every list stale', async () => {
    const status = changeStatus(answer(409, { detail: "Can't start a task that is done." }))
    server.use(...status.handlers)
    const { queryClient, change } = await renderTransition()

    await act(() => change('start'))

    expect(queryClient.getQueryData(detailKey)).toEqual(invoice)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })
})

describe('an assignment', () => {
  it.each([
    ['assigns', 2, summaryOf(users.bob)],
    ['unassigns, with null', null, null],
  ] as const)('%s, then caches the task it returns', async (_, assigneeId, assignee) => {
    const assigned = { ...invoice, assignee }
    const request = assignTask(assigned)
    server.use(request.handler)
    const { queryClient, assign } = await renderAssign()

    await act(() => assign(assigneeId))

    expect(request.bodies()).toEqual([{ assignee_id: assigneeId }])
    expect(queryClient.getQueryData(detailKey)).toEqual(assigned)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('a 400 for an assignee no longer active changes nothing in the cache', async () => {
    server.use(assignTask(answer(400, { assignee_id: ['Must be an active user.'] })).handler)
    const { queryClient, assign } = await renderAssign()

    await act(() => assign(3))

    expect(queryClient.getQueryData(detailKey)).toEqual(invoice)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(false)
  })
})
