import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, type JsonBodyType } from 'msw'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../test/api'
import { admin, currentUser, refreshAnswers, users } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, deleteTask, getTask, held, listTasks, summaryOf } from '../../test/tasks'

// Delete, always after a confirmation (spec section 8), by the owner or an admin (spec
// section 3), from the More menu on the task page and in the list.

const invoice = aTask({
  id: 7,
  title: 'Send the October invoice',
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
})

function openTask(
  answers: Parameters<typeof deleteTask> = [],
  me: Schemas['CurrentUser'] = users.alice,
) {
  const remove = deleteTask(...answers)
  const get = getTask(invoice)
  const list = listTasks(aPage([]))
  server.use(
    refreshAnswers('alice-token').handler,
    currentUser(me),
    get.handler,
    list.handler,
    remove.handler,
  )
  return { ...renderApp({ path: '/tasks/7' }), remove, get, list }
}

async function openDelete() {
  await userEvent.click(await screen.findByRole('button', { name: 'More' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Delete…' }))
  return within(await screen.findByRole('dialog', { name: 'Delete task' }))
}

function answer(status: number, body: JsonBodyType, headers: Record<string, string> = {}) {
  return () => HttpResponse.json(body, { status, headers })
}

describe('asking first', () => {
  it.each([
    ['the owner', users.alice],
    ['an admin', admin],
  ])('%s gets Delete… in the More menu, which asks before deleting', async (_, me) => {
    const { remove } = openTask([], me)

    const dialog = await openDelete()

    expect(dialog.getByText(/Send the October invoice/)).toBeInTheDocument()
    expect(dialog.getByText(/There's no undo/)).toBeInTheDocument()
    expect(remove.ids()).toEqual([])
  })

  it('Cancel closes the dialog and deletes nothing', async () => {
    const { remove } = openTask()
    const dialog = await openDelete()

    await userEvent.click(dialog.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog', { name: 'Delete task' })).not.toBeInTheDocument()
    expect(remove.ids()).toEqual([])
  })
})

describe('deleting', () => {
  it('from the task page: deletes, says so, and goes to the list without reloading the task', async () => {
    const { remove, get, router } = openTask()
    const dialog = await openDelete()

    await userEvent.click(dialog.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('Task deleted.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Tasks' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks')
    expect(remove.ids()).toEqual(['7'])
    // The deleted task was never asked for again.
    expect(get.ids()).toEqual(['7'])
  })

  it('from the list: the list refetches without the task', async () => {
    const remove = deleteTask()
    const list = listTasks(aPage([invoice]), aPage([]))
    server.use(refreshAnswers('alice-token').handler, list.handler, remove.handler)
    renderApp({ path: '/tasks' })
    const card = within(await screen.findByRole('listitem'))

    await userEvent.click(await card.findByRole('button', { name: 'More' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Delete…' }))
    await userEvent.click(
      within(await screen.findByRole('dialog', { name: 'Delete task' })).getByRole('button', {
        name: 'Delete',
      }),
    )

    expect(await screen.findByText('Task deleted.')).toBeInTheDocument()
    expect(await screen.findByText('No tasks yet')).toBeInTheDocument()
    expect(remove.ids()).toEqual(['7'])
    expect(list.requests()).toHaveLength(2)
  })

  it("while it runs, the dialog can't be closed and the task's other actions wait", async () => {
    const response = held()
    openTask([
      async () => {
        await response.wait
        return new HttpResponse(null, { status: 204 })
      },
    ])
    const dialog = await openDelete()

    await userEvent.click(dialog.getByRole('button', { name: 'Delete' }))

    expect(dialog.getByRole('button', { name: 'Delete' })).toHaveAttribute('data-loading', 'true')
    expect(dialog.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(dialog.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('dialog', { name: 'Delete task' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'More', hidden: true })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Start', hidden: true })).toBeDisabled()

    response.release()

    expect(await screen.findByText('Task deleted.')).toBeInTheDocument()
  })
})

describe("the API's refusals", () => {
  it.each([
    [
      403,
      { detail: "Only the task's owner or an admin can delete." },
      'Not allowed',
      "Only the task's owner or an admin can delete.",
    ],
    [429, { detail: 'Request was throttled.' }, 'Too many requests', 'Try again in 30 seconds.'],
  ] as const)('a %i is explained in the dialog', async (status, body, title, message) => {
    openTask([answer(status, body, { 'Retry-After': '30' })])
    const dialog = await openDelete()

    await userEvent.click(dialog.getByRole('button', { name: 'Delete' }))

    const alert = await dialog.findByRole('alert')
    expect(alert).toHaveTextContent(title)
    expect(alert).toHaveTextContent(message)
  })

  it('a 404: the task was already gone, and the page says so', async () => {
    openTask([answer(404, { detail: 'Not found.' })])
    server.use(getTask(invoice, answer(404, { detail: 'Not found.' })).handler)
    const dialog = await openDelete()

    await userEvent.click(dialog.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByRole('link', { name: 'Back to tasks' })).toBeInTheDocument()
    expect(screen.getAllByText('Task not found').length).toBeGreaterThan(0)
  })
})
