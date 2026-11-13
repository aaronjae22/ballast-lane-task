import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { refreshAnswers, users } from '../../test/handlers'
import { onWideScreen } from '../../test/media'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, held, listTasks, summaryOf } from '../../test/tasks'

const invoice = aTask({
  id: 7,
  title: 'Send the October invoice',
  status: 'in_progress',
  due_date: '2026-11-05',
  is_overdue: true,
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
})
const handbook = aTask({
  id: 8,
  title: 'Write the team handbook',
  status: 'done',
  due_date: null,
  owner: summaryOf(users.bob),
  assignee: null,
})

function openList(path = '/tasks', ...answers: Parameters<typeof listTasks>) {
  const list = listTasks(...answers)
  server.use(refreshAnswers('alice-token').handler, list.handler)
  return { ...renderApp({ path }), list }
}

describe('the task list on a narrow screen', () => {
  it('shows each task as a card with its title, status, due date, owner and assignee', async () => {
    openList('/tasks', aPage([invoice, handbook]))

    const cards = within(await screen.findByRole('list', { name: 'Tasks' })).getAllByRole(
      'listitem',
    )
    expect(cards).toHaveLength(2)
    const [first, second] = cards as [HTMLElement, HTMLElement]
    expect(within(first).getByRole('link', { name: 'Send the October invoice' })).toHaveAttribute(
      'href',
      '/tasks/7',
    )
    expect(first).toHaveTextContent('In progress')
    // A plain day: in Los Angeles, midnight UTC on Nov 5 would show Nov 4.
    expect(first).toHaveTextContent('Due Nov 5, 2026')
    expect(within(first).getByText('Overdue')).toBeInTheDocument()
    expect(first).toHaveTextContent('Owner: Alice Johnson')
    expect(first).toHaveTextContent('Assignee: Bob Smith')

    expect(second).toHaveTextContent('Done')
    expect(second).toHaveTextContent('No due date')
    expect(second).toHaveTextContent('Assignee: Unassigned')
    expect(within(second).queryByText('Overdue')).not.toBeInTheDocument()
  })

  it('shows how many tasks match, across every page', async () => {
    openList('/tasks', aPage([invoice], { count: 21 }))

    expect(await screen.findByText('21 tasks')).toBeInTheDocument()
  })

  it('links to the create page', async () => {
    openList('/tasks', aPage([invoice]))

    expect(await screen.findByRole('link', { name: 'New task' })).toHaveAttribute(
      'href',
      '/tasks/new',
    )
  })
})

describe('the task list on a wide screen', () => {
  let restore: () => void = () => undefined
  afterEach(() => {
    restore()
  })

  it('shows a table with a column for each detail', async () => {
    restore = onWideScreen()
    openList('/tasks', aPage([invoice, handbook]))

    const table = await screen.findByRole('table', { name: 'Tasks' })
    const headers = within(table)
      .getAllByRole('columnheader')
      .map((header) => header.textContent)
    expect(headers).toEqual(['Title', 'Status', 'Due date', 'Owner', 'Assignee'])
    const row = within(table).getByRole('row', { name: /Send the October invoice/ })
    expect(row).toHaveTextContent('Nov 5, 2026')
    expect(within(row).getByText('Overdue')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Tasks' })).not.toBeInTheDocument()
  })
})

describe('the states around the list', () => {
  it('shows a loader until the tasks arrive', async () => {
    const gate = held()
    openList('/tasks', async () => {
      await gate.wait
      return HttpResponse.json(aPage([invoice]))
    })

    expect(await screen.findByRole('status', { name: 'Loading tasks' })).toBeInTheDocument()
    gate.release()
    expect(await screen.findByText('Send the October invoice')).toBeInTheDocument()
    expect(screen.queryByRole('status', { name: 'Loading tasks' })).not.toBeInTheDocument()
  })

  it('without filters and without tasks, invites the user to create one', async () => {
    openList('/tasks', aPage([]))

    expect(await screen.findByText('No tasks yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Create a task' })).toHaveAttribute(
      'href',
      '/tasks/new',
    )
  })

  it('with filters and without tasks, offers to clear the filters', async () => {
    const { router } = openList('/tasks?status=done&search=report', aPage([]))

    expect(await screen.findByText('No tasks match these filters')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(router.state.location.search).toBe('')
  })

  it("says when the server can't be reached, and tries again", async () => {
    const { list } = openList(
      '/tasks',
      () => HttpResponse.json({ detail: 'Server error.' }, { status: 500 }),
      aPage([invoice]),
    )

    expect(await screen.findByText("Can't reach the server")).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Send the October invoice')).toBeInTheDocument()
    expect(list.requests()).toHaveLength(2)
  })

  it('a request with no answer says the same', async () => {
    openList('/tasks', () => HttpResponse.error())

    expect(await screen.findByText("Can't reach the server")).toBeInTheDocument()
  })

  it('when throttled, says when to try again', async () => {
    openList('/tasks', () =>
      HttpResponse.json(
        { detail: 'Request was throttled.' },
        { status: 429, headers: { 'Retry-After': '30' } },
      ),
    )

    expect(await screen.findByText('Try again in 30 seconds.')).toBeInTheDocument()
  })
})
