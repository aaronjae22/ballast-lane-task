import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { admin, currentUser, refreshAnswers, users } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aTask, getTask, held, summaryOf } from '../../test/tasks'

const invoice = aTask({
  id: 7,
  title: 'Send the October invoice',
  description: 'To the Acme account.\nCopy finance.',
  status: 'in_progress',
  due_date: '2026-11-05',
  is_overdue: true,
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
  created_at: '2026-10-30T17:05:00Z',
  updated_at: '2026-11-13T02:30:00Z',
})

function openTask(path: string, ...answers: Parameters<typeof getTask>) {
  const get = getTask(...answers)
  server.use(refreshAnswers('alice-token').handler, get.handler)
  return { ...renderApp({ path }), get }
}

/** The value shown for a label in the task's details. */
function detail(label: string): string | null {
  return screen.getByText(label, { selector: 'dt' }).nextElementSibling?.textContent ?? null
}

describe('a task', () => {
  it('shows its title, status, description, due date, owner, assignee and times', async () => {
    const { get } = openTask('/tasks/7', invoice)

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Send the October invoice' }),
    ).toBeInTheDocument()
    expect(screen.getByText('In progress')).toBeInTheDocument()
    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText(/To the Acme account\./)).toHaveTextContent(
      'To the Acme account. Copy finance.',
    )
    expect(detail('Due date')).toBe('Nov 5, 2026')
    expect(detail('Owner')).toBe('Alice Johnson')
    expect(detail('Assignee')).toBe('Bob Smith')
    // In the browser's time zone, Los Angeles in this run: daylight time, then standard time.
    expect(detail('Created')).toBe('Oct 30, 2026, 10:05 AM')
    expect(detail('Updated')).toBe('Nov 12, 2026, 6:30 PM')
    expect(screen.queryByText('Completed', { selector: 'dt' })).not.toBeInTheDocument()
    expect(get.ids()).toEqual(['7'])
  })

  it('says when it has no description, due date or assignee', async () => {
    openTask('/tasks/8', aTask({ id: 8, description: '', due_date: null, assignee: null }))

    expect(await screen.findByText('No description')).toBeInTheDocument()
    expect(detail('Due date')).toBe('No due date')
    expect(detail('Assignee')).toBe('Unassigned')
    expect(screen.queryByText('Overdue')).not.toBeInTheDocument()
  })

  it('shows when a done task was completed', async () => {
    openTask('/tasks/9', aTask({ id: 9, status: 'done', completed_at: '2026-11-12T17:05:00Z' }))

    expect(await screen.findByText('Done')).toBeInTheDocument()
    expect(detail('Completed')).toBe('Nov 12, 2026, 9:05 AM')
  })

  it('links back to the list', async () => {
    openTask('/tasks/7', invoice)

    expect(await screen.findByRole('link', { name: 'Back to tasks' })).toHaveAttribute(
      'href',
      '/tasks',
    )
  })
})

// Edit sits in the More menu with Assign and Delete (ADR 0018).
describe('the Edit link', () => {
  it.each([
    ['the owner', users.alice],
    ['an admin', admin],
  ])('%s gets one in the More menu, to the edit page', async (_, me) => {
    server.use(currentUser(me))
    openTask('/tasks/7', invoice)

    await userEvent.click(await screen.findByRole('button', { name: 'More' }))

    expect(await screen.findByRole('menuitem', { name: 'Edit' })).toHaveAttribute(
      'href',
      '/tasks/7/edit',
    )
  })

  it("the assignee doesn't: only the owner or an admin may edit (spec section 3)", async () => {
    server.use(currentUser(users.bob))
    openTask('/tasks/7', invoice)

    // Once the header shows who is signed in, the page knows it too.
    expect(await within(await screen.findByRole('banner')).findByText('Bob Smith')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Send the October invoice' })).toBeInTheDocument()
    // Nothing in the menu is the assignee's to do, so there's no menu.
    expect(screen.queryByRole('button', { name: 'More' })).not.toBeInTheDocument()
  })
})

describe('while it loads, and when it fails', () => {
  it('shows a loading state until the task arrives', async () => {
    const response = held()
    openTask('/tasks/7', async () => {
      await response.wait
      return HttpResponse.json(invoice)
    })

    expect(await screen.findByRole('status', { name: 'Loading the task' })).toBeInTheDocument()
    response.release()
    expect(
      await screen.findByRole('heading', { name: 'Send the October invoice' }),
    ).toBeInTheDocument()
  })

  it("a 404 says the task isn't there, with a way back and no retry", async () => {
    openTask('/tasks/7', () => HttpResponse.json({ detail: 'Not found.' }, { status: 404 }))

    expect(await screen.findByText('Task not found')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to tasks' })).toHaveAttribute('href', '/tasks')
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it.each(['abc', '0', '7.5', '99999999999999999999'])(
    'an id that is no task, /tasks/%s, says so without asking the API',
    async (id) => {
      const { get } = openTask(`/tasks/${id}`, invoice)

      expect(await screen.findByText('Task not found')).toBeInTheDocument()
      expect(get.ids()).toEqual([])
    },
  )

  it("can't reach the server: says so, and Try again loads it", async () => {
    const { get } = openTask(
      '/tasks/7',
      () => HttpResponse.json({ detail: 'Server error' }, { status: 503 }),
      invoice,
    )

    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))

    expect(
      await screen.findByRole('heading', { name: 'Send the October invoice' }),
    ).toBeInTheDocument()
    expect(get.ids()).toEqual(['7', '7'])
  })
})
