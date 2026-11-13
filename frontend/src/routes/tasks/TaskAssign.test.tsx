import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, type JsonBodyType } from 'msw'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../test/api'
import { admin, currentUser, refreshAnswers, users } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, assignTask, getTask, held, listTasks, summaryOf } from '../../test/tasks'

// Assign, reassign and unassign (spec section 3), from the More menu on the task page and in
// the list. The picker offers the active users from /api/users/ (ADR 0018).

const invoice = aTask({
  id: 7,
  title: 'Send the October invoice',
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
})

function openTask(
  answers: Parameters<typeof assignTask>,
  {
    task = invoice,
    me = users.alice,
  }: { task?: Schemas['Task']; me?: Schemas['CurrentUser'] } = {},
) {
  const assign = assignTask(...answers)
  server.use(
    refreshAnswers('alice-token').handler,
    currentUser(me),
    getTask(task).handler,
    assign.handler,
  )
  return { ...renderApp({ path: '/tasks/7' }), assign }
}

async function openAssign() {
  await userEvent.click(await screen.findByRole('button', { name: 'More' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Assign…' }))
  return within(await screen.findByRole('dialog', { name: 'Assign task' }))
}

async function pick(name: string) {
  await userEvent.click(screen.getByRole('combobox', { name: 'Assignee' }))
  await userEvent.click(await screen.findByRole('option', { name }))
}

function detail(label: string): string | null {
  return screen.getByText(label, { selector: 'dt' }).nextElementSibling?.textContent ?? null
}

function answer(status: number, body: JsonBodyType, headers: Record<string, string> = {}) {
  return () => HttpResponse.json(body, { status, headers })
}

describe('who may assign', () => {
  it.each([
    ['the owner', users.alice],
    ['an admin', admin],
  ])('%s gets Assign… in the More menu', async (_, me) => {
    openTask([invoice], { me })

    await userEvent.click(await screen.findByRole('button', { name: 'More' }))

    expect(await screen.findByRole('menuitem', { name: 'Assign…' })).toBeInTheDocument()
  })
})

describe('the Assign dialog', () => {
  it('shows the current assignee, and offers Unassigned and the active users', async () => {
    openTask([invoice])
    const dialog = await openAssign()

    expect(dialog.getByRole('combobox', { name: 'Assignee' })).toHaveValue('Bob Smith')
    await userEvent.click(dialog.getByRole('combobox', { name: 'Assignee' }))
    expect((await screen.findAllByRole('option')).map((option) => option.textContent)).toEqual([
      'Unassigned',
      'Alice Johnson',
      'Bob Smith',
      'Carol Diaz',
    ])
  })

  it('reassigns to someone else, says so, and shows the new assignee', async () => {
    const { assign } = openTask([{ ...invoice, assignee: summaryOf(users.carol) }])
    const dialog = await openAssign()

    await pick('Carol Diaz')
    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Assigned to Carol Diaz.')).toBeInTheDocument()
    expect(assign.bodies()).toEqual([{ assignee_id: 3 }])
    expect(screen.queryByRole('dialog', { name: 'Assign task' })).not.toBeInTheDocument()
    expect(detail('Assignee')).toBe('Carol Diaz')
  })

  // An option, not only the Select's clear button, which is hidden from the keyboard and
  // from screen readers.
  it('unassigns with the Unassigned option, sending null', async () => {
    const { assign } = openTask([{ ...invoice, assignee: null }])
    const dialog = await openAssign()

    await pick('Unassigned')
    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Task unassigned.')).toBeInTheDocument()
    expect(assign.bodies()).toEqual([{ assignee_id: null }])
    expect(detail('Assignee')).toBe('Unassigned')
  })

  it('still shows a current assignee who is no longer active', async () => {
    const task = { ...invoice, assignee: { id: 9, name: 'Dan Former' } }
    openTask([task], { task })

    const dialog = await openAssign()

    expect(dialog.getByRole('combobox', { name: 'Assignee' })).toHaveValue('Dan Former')
  })

  it.each([
    ['Save, with nothing changed,', 'Save'],
    ['Cancel', 'Cancel'],
  ])('%s closes it and sends nothing', async (_, button) => {
    const { assign } = openTask([invoice])
    const dialog = await openAssign()

    await userEvent.click(dialog.getByRole('button', { name: button }))

    expect(screen.queryByRole('dialog', { name: 'Assign task' })).not.toBeInTheDocument()
    expect(assign.bodies()).toEqual([])
  })
})

describe('while it saves', () => {
  // Closing the dialog mid-save and opening it again would start a second assignment, which
  // could finish first and be overwritten by the earlier one (ADR 0018: the task's other
  // actions wait for a running change).
  it("the dialog can't be closed, and the task's other actions wait", async () => {
    const response = held()
    const { assign } = openTask([
      async () => {
        await response.wait
        return HttpResponse.json({ ...invoice, assignee: summaryOf(users.carol) })
      },
    ])
    const dialog = await openAssign()
    await pick('Carol Diaz')

    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    expect(dialog.getByRole('button', { name: 'Save' })).toHaveAttribute('data-loading', 'true')
    expect(dialog.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(dialog.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('dialog', { name: 'Assign task' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'More', hidden: true })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Start', hidden: true })).toBeDisabled()

    response.release()

    expect(await screen.findByText('Assigned to Carol Diaz.')).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Assign task' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'More' })).toBeEnabled()
    expect(assign.bodies()).toHaveLength(1)
  })

  it('can be closed with its Close button when nothing is saving', async () => {
    openTask([invoice])
    const dialog = await openAssign()

    await userEvent.click(dialog.getByRole('button', { name: 'Close' }))

    expect(screen.queryByRole('dialog', { name: 'Assign task' })).not.toBeInTheDocument()
  })
})

describe("the API's refusals", () => {
  it('a 400 for a user deactivated since goes on the field, and the dialog stays', async () => {
    openTask([answer(400, { assignee_id: ['Must be an active user.'] })])
    const dialog = await openAssign()

    await pick('Carol Diaz')
    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    expect(await dialog.findByRole('combobox', { name: 'Assignee' })).toHaveAccessibleDescription(
      'Must be an active user.',
    )
  })

  it('a 429 says when to try again, in the dialog', async () => {
    openTask([answer(429, { detail: 'Request was throttled.' }, { 'Retry-After': '30' })])
    const dialog = await openAssign()

    await pick('Carol Diaz')
    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    const alert = await dialog.findByRole('alert')
    expect(alert).toHaveTextContent('Too many requests')
    expect(alert).toHaveTextContent('Try again in 30 seconds.')
  })

  it('a 404 says the task is gone', async () => {
    openTask([answer(404, { detail: 'Not found.' })])
    server.use(getTask(invoice, answer(404, { detail: 'Not found.' })).handler)
    const dialog = await openAssign()

    await pick('Carol Diaz')
    await userEvent.click(dialog.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('link', { name: 'Back to tasks' })).toBeInTheDocument()
    expect(screen.getAllByText('Task not found').length).toBeGreaterThan(0)
  })
})

describe('from the list', () => {
  it("a card's More menu assigns that task", async () => {
    const assign = assignTask({ ...invoice, assignee: summaryOf(users.carol) })
    server.use(
      refreshAnswers('alice-token').handler,
      listTasks(aPage([invoice])).handler,
      assign.handler,
    )
    renderApp({ path: '/tasks' })
    const card = within(await screen.findByRole('listitem'))

    await userEvent.click(await card.findByRole('button', { name: 'More' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Assign…' }))
    await screen.findByRole('dialog', { name: 'Assign task' })
    await pick('Carol Diaz')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Assigned to Carol Diaz.')).toBeInTheDocument()
    expect(assign.bodies()).toEqual([{ assignee_id: 3 }])
  })
})
