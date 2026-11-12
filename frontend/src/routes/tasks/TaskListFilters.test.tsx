import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { activeUsers, refreshAnswers, users } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, listTasks } from '../../test/tasks'

function openList(path = '/tasks') {
  const list = listTasks(aPage([aTask({ title: 'Send the October invoice' })]))
  server.use(refreshAnswers('alice-token').handler, list.handler)
  const app = renderApp({ path })
  const lastQuery = () => list.requests().at(-1)?.searchParams ?? new URLSearchParams()
  return { ...app, lastQuery }
}

// On a narrow screen, as in every test here unless it says otherwise, the filters fold away.
// The panel shows a render after the click (Mantine's Collapse keeps it in React's Activity),
// so this waits until its fields can be seen.
async function openFilters() {
  await userEvent.click(await screen.findByRole('button', { name: /^Filters/ }))
  await screen.findByRole('group', { name: 'Status' })
}

afterEach(() => {
  vi.useRealTimers()
})

describe('the status filter', () => {
  it('takes several statuses, each one added to the URL', async () => {
    const { router, lastQuery } = openList()
    await openFilters()

    await userEvent.click(screen.getByRole('checkbox', { name: 'To do' }))
    await userEvent.click(screen.getByRole('checkbox', { name: 'Done' }))

    expect(router.state.location.search).toBe('?status=to_do&status=done')
    await waitFor(() => {
      expect(lastQuery().getAll('status')).toEqual(['to_do', 'done'])
    })
    await userEvent.click(screen.getByRole('checkbox', { name: 'To do' }))
    expect(router.state.location.search).toBe('?status=done')
  })
})

describe('the overdue filter', () => {
  it('chooses between any, overdue and not overdue', async () => {
    const { router } = openList()
    await openFilters()

    await userEvent.click(screen.getByRole('radio', { name: 'Overdue' }))
    expect(router.state.location.search).toBe('?overdue=true')
    await userEvent.click(screen.getByRole('radio', { name: 'Not overdue' }))
    expect(router.state.location.search).toBe('?overdue=false')
    await userEvent.click(screen.getByRole('radio', { name: 'Any' }))
    expect(router.state.location.search).toBe('')
  })
})

describe('the assignee filter', () => {
  it('offers "Me" and every active user from /api/users/', async () => {
    const { router } = openList()
    await openFilters()

    await userEvent.click(screen.getByRole('combobox', { name: 'Assignee' }))
    const names = (await screen.findAllByRole('option')).map((option) => option.textContent)
    expect(names).toEqual(['Me', 'Alice Johnson', 'Bob Smith', 'Carol Diaz'])
    await userEvent.click(screen.getByRole('option', { name: 'Bob Smith' }))

    expect(router.state.location.search).toBe(`?assignee=${String(users.bob.id)}`)
  })

  it('"Me" is sent as me, which the API resolves to the signed-in user', async () => {
    const { router } = openList()
    await openFilters()

    await userEvent.click(screen.getByRole('combobox', { name: 'Assignee' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Me' }))

    expect(router.state.location.search).toBe('?assignee=me')
  })

  it('shows a user from a link who is no longer active by their id', async () => {
    server.use(activeUsers([users.alice]))
    openList('/tasks?assignee=99')
    await openFilters()

    expect(screen.getByRole('combobox', { name: 'Assignee' })).toHaveValue('User #99')
  })
})

describe('the due date range', () => {
  it('shows the days from a link as plain days, and clears one', async () => {
    const { router } = openList('/tasks?due_after=2026-11-01&due_before=2026-11-30')
    await openFilters()

    expect(screen.getByRole('button', { name: 'Due from' })).toHaveTextContent('Nov 1, 2026')
    expect(screen.getByRole('button', { name: 'Due until' })).toHaveTextContent('Nov 30, 2026')
    await userEvent.click(screen.getByRole('button', { name: 'Clear due from' }))

    expect(router.state.location.search).toBe('?due_before=2026-11-30')
  })

  it('a picked day goes to the URL as YYYY-MM-DD, never shifted a day', async () => {
    // Only Date is faked, so the calendar opens on November 2026 and timers still run.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 12, 18, 30))
    const { router } = openList()
    await openFilters()

    await userEvent.click(screen.getByRole('button', { name: 'Due until' }))
    await userEvent.click(await screen.findByRole('button', { name: '20 November 2026' }))

    expect(router.state.location.search).toBe('?due_before=2026-11-20')
  })
})

describe('on a narrow screen', () => {
  it('folds the filters behind a button that counts the active ones', async () => {
    openList('/tasks?status=done&overdue=true&search=invoice')

    const toggle = await screen.findByRole('button', { name: 'Filters (2)' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    // The search box stays out, where it can be reached at once.
    expect(screen.getByRole('searchbox', { name: 'Search titles' })).toBeVisible()
    expect(screen.queryByRole('group', { name: 'Status' })).not.toBeInTheDocument()
    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    const status = await screen.findByRole('group', { name: 'Status' })
    expect(within(status).getAllByRole('checkbox')).toHaveLength(3)
  })
})
