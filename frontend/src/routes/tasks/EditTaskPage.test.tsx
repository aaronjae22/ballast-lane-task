import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, type JsonBodyType } from 'msw'
import { describe, expect, it } from 'vitest'
import { admin, currentUser, refreshAnswers, users } from '../../test/handlers'
import type { Schemas } from '../../test/api'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aTask, getTask, summaryOf, updateTask } from '../../test/tasks'

// Overdue: its due date is past, which ADR 0012 accepts only when it isn't changed.
const invoice = aTask({
  id: 7,
  title: 'Send the October invoice',
  description: 'To the Acme account.',
  status: 'in_progress',
  due_date: '2026-11-05',
  is_overdue: true,
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
})
const renamed = { ...invoice, title: 'Send the November invoice' }

interface EditOptions {
  path?: string
  /** The answers to GET /api/tasks/7/: the edit page's load, then the task page's. */
  tasks?: Parameters<typeof getTask>
  updates?: Parameters<typeof updateTask>
  me?: Schemas['CurrentUser']
}

function openEdit({
  path = '/tasks/7/edit',
  tasks = [invoice, renamed],
  updates = [renamed],
  me = users.alice,
}: EditOptions = {}) {
  const get = getTask(...tasks)
  const update = updateTask(...updates)
  server.use(refreshAnswers('alice-token').handler, currentUser(me), get.handler, update.handler)
  return { ...renderApp({ path }), get, update }
}

async function titleField() {
  return screen.findByRole('textbox', { name: 'Title' })
}

async function save() {
  await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
}

function answer(status: number, body: JsonBodyType) {
  return () => HttpResponse.json(body, { status })
}

describe('the edit form', () => {
  it("opens with the task's title, description and due date, and no assignee", async () => {
    openEdit()

    expect(await screen.findByRole('heading', { name: 'Edit task' })).toBeInTheDocument()
    expect(await titleField()).toHaveValue('Send the October invoice')
    expect(screen.getByRole('textbox', { name: 'Description' })).toHaveValue('To the Acme account.')
    expect(screen.getByRole('button', { name: 'Due date' })).toHaveTextContent('Nov 5, 2026')
    // Assigning has its own action and endpoint (ADR 0004).
    expect(screen.queryByRole('combobox', { name: 'Assignee' })).not.toBeInTheDocument()
  })

  it('Cancel goes back to the task', async () => {
    openEdit()

    expect(await screen.findByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/tasks/7')
  })
})

describe('saving', () => {
  it('renames an overdue task without sending its due date back, then shows it', async () => {
    const { update, router } = openEdit()
    const title = await titleField()

    await userEvent.clear(title)
    await userEvent.type(title, 'Send the November invoice ')
    await save()

    expect(await screen.findByText('Changes saved.')).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Send the November invoice' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks/7')
    expect(update.bodies()).toEqual([{ title: 'Send the November invoice' }])
  })

  it('a cleared due date is sent as null, and nothing else', async () => {
    const { update } = openEdit({ updates: [{ ...invoice, due_date: null, is_overdue: false }] })
    await titleField()

    await userEvent.click(screen.getByRole('button', { name: 'Clear due date' }))
    await save()

    await screen.findByText('Changes saved.')
    expect(update.bodies()).toEqual([{ due_date: null }])
  })

  it('a changed description is sent alone', async () => {
    const { update } = openEdit()
    await titleField()
    const description = screen.getByRole('textbox', { name: 'Description' })

    await userEvent.type(description, ' Copy finance.')
    await save()

    await screen.findByText('Changes saved.')
    expect(update.bodies()).toEqual([{ description: 'To the Acme account. Copy finance.' }])
  })

  it('with nothing changed, sends nothing and goes back to the task', async () => {
    const { update, router } = openEdit()
    await titleField()

    await save()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Send the October invoice' }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks/7')
    expect(update.bodies()).toEqual([])
  })
})

describe("the API's answers", () => {
  it('a 400 goes on its field', async () => {
    openEdit({ updates: [answer(400, { title: ['Must be 1 to 200 characters.'] })] })
    await userEvent.type(await titleField(), '!')

    await save()

    expect(await titleField()).toHaveAccessibleDescription('Must be 1 to 200 characters.')
  })

  it("a 403 says why, in the API's words", async () => {
    openEdit({
      updates: [answer(403, { detail: "Only the task's owner or an admin can edit." })],
    })
    await userEvent.type(await titleField(), '!')

    await save()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Not allowed')
    expect(alert).toHaveTextContent("Only the task's owner or an admin can edit.")
  })

  it('a 404 says the task is gone', async () => {
    openEdit({
      tasks: [invoice, answer(404, { detail: 'Not found.' })],
      updates: [answer(404, { detail: 'Not found.' })],
    })
    await userEvent.type(await titleField(), '!')

    await save()

    expect(await screen.findByRole('link', { name: 'Back to tasks' })).toBeInTheDocument()
    expect(screen.getByText('Task not found')).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Title' })).not.toBeInTheDocument()
  })
})

describe('who may edit', () => {
  it('the assignee is told only the owner or an admin can, and gets no form', async () => {
    openEdit({ me: users.bob })

    expect(
      await screen.findByText("Only the task's owner or an admin can edit it."),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the task' })).toHaveAttribute(
      'href',
      '/tasks/7',
    )
    expect(screen.queryByRole('textbox', { name: 'Title' })).not.toBeInTheDocument()
  })

  it('an admin may edit a task someone else owns', async () => {
    openEdit({ me: admin })

    expect(await titleField()).toHaveValue('Send the October invoice')
  })
})

describe('a task that is not there', () => {
  it.each([
    ['a 404', '/tasks/7/edit'],
    ['an id that is no task', '/tasks/abc/edit'],
  ])('%s says so', async (_, path) => {
    const { get } = openEdit({ path, tasks: [answer(404, { detail: 'Not found.' })] })

    expect(await screen.findByText('Task not found')).toBeInTheDocument()
    expect(get.ids()).toEqual(path === '/tasks/7/edit' ? ['7'] : [])
  })
})
