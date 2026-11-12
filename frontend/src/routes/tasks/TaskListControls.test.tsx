import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { refreshAnswers } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, listTasks } from '../../test/tasks'

function openList(path: string, ...answers: Parameters<typeof listTasks>) {
  const list = listTasks(...answers)
  server.use(refreshAnswers('alice-token').handler, list.handler)
  const app = renderApp({ path })
  const lastQuery = () => list.requests().at(-1)?.searchParams ?? new URLSearchParams()
  return { ...app, list, lastQuery }
}

const onePage = aPage([aTask({ title: 'Send the October invoice' })])
const threePages = aPage([aTask({ title: 'Send the October invoice' })], { count: 45 })

describe('pagination', () => {
  it('asks for pages of 20, and shows a page button for each page', async () => {
    const { lastQuery } = openList('/tasks', threePages)

    expect(await screen.findByRole('button', { name: '3' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '4' })).not.toBeInTheDocument()
    expect(lastQuery().get('page_size')).toBe('20')
  })

  it('goes to another page through the URL, so Back returns to the first', async () => {
    const { router, lastQuery } = openList('/tasks', threePages)

    await userEvent.click(await screen.findByRole('button', { name: '2' }))

    expect(router.state.location.search).toBe('?page=2')
    await waitFor(() => {
      expect(lastQuery().get('page')).toBe('2')
    })
    await router.navigate(-1)
    expect(router.state.location.search).toBe('')
  })

  it('has no pagination when everything fits on one page', async () => {
    openList('/tasks', onePage)

    await screen.findByText('Send the October invoice')
    expect(screen.queryByRole('button', { name: '1' })).not.toBeInTheDocument()
  })

  it('a page past the end says so, and goes back to page 1', async () => {
    const { router } = openList(
      '/tasks?status=to_do&page=9',
      () => HttpResponse.json({ detail: 'Invalid page.' }, { status: 404 }),
      onePage,
    )

    expect(await screen.findByText('No tasks on page 9')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Go to page 1' }))
    expect(router.state.location.search).toBe('?status=to_do')
    expect(await screen.findByText('Send the October invoice')).toBeInTheDocument()
  })
})

describe('ordering', () => {
  it('orders by the soonest due date unless another order is chosen', async () => {
    const { router, lastQuery } = openList('/tasks', onePage)

    const order = await screen.findByRole('combobox', { name: 'Order' })
    expect(order).toHaveValue('Due date, soonest first')
    await userEvent.click(order)
    await userEvent.click(await screen.findByRole('option', { name: 'Newest first' }))

    expect(router.state.location.search).toBe('?ordering=-created_at')
    await waitFor(() => {
      expect(lastQuery().get('ordering')).toBe('-created_at')
    })
  })

  it('choosing the default order again leaves it out of the URL', async () => {
    const { router } = openList('/tasks?ordering=status', onePage)

    await userEvent.click(await screen.findByRole('combobox', { name: 'Order' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Due date, soonest first' }))

    expect(router.state.location.search).toBe('')
  })
})

describe('title search', () => {
  it('searches once the user stops typing, not on every key', async () => {
    const { router, list, lastQuery } = openList('/tasks', onePage)
    const box = await screen.findByRole('searchbox', { name: 'Search titles' })

    await userEvent.type(box, 'invoice')

    await waitFor(() => {
      expect(router.state.location.search).toBe('?search=invoice')
    })
    await waitFor(() => {
      expect(lastQuery().get('search')).toBe('invoice')
    })
    // The first load and the search, never one request per letter.
    expect(list.requests()).toHaveLength(2)
  })

  it('starting a search adds a history entry, and refining it replaces that entry', async () => {
    const { router } = openList('/tasks', onePage)
    const box = await screen.findByRole('searchbox', { name: 'Search titles' })

    await userEvent.type(box, 'invoice')
    await waitFor(() => {
      expect(router.state.location.search).toBe('?search=invoice')
    })
    expect(router.state.historyAction).toBe('PUSH')
    await userEvent.type(box, ' oct')
    await waitFor(() => {
      expect(router.state.location.search).toBe('?search=invoice+oct')
    })
    expect(router.state.historyAction).toBe('REPLACE')

    await router.navigate(-1)
    expect(router.state.location.search).toBe('')
    await waitFor(() => {
      expect(box).toHaveValue('')
    })
  })

  // Longer than the search box's 300 ms wait, so a pending search would have fired.
  const afterTheWait = () => act(() => new Promise<void>((resolve) => setTimeout(resolve, 400)))

  it("Back while a refinement is still waiting drops it, so Back isn't undone", async () => {
    const { router } = openList('/tasks', onePage)
    const box = await screen.findByRole('searchbox', { name: 'Search titles' })
    await userEvent.type(box, 'invoice')
    await waitFor(() => {
      expect(router.state.location.search).toBe('?search=invoice')
    })

    await userEvent.type(box, ' oct')
    await act(() => router.navigate(-1))
    await afterTheWait()

    expect(router.state.location.search).toBe('')
    expect(box).toHaveValue('')
  })

  it('Clear filters while a refinement is still waiting drops it', async () => {
    const { router } = openList('/tasks?search=invoice', aPage([]))
    const box = await screen.findByRole('searchbox', { name: 'Search titles' })
    await screen.findByText('No tasks match these filters')

    await userEvent.type(box, ' oct')
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    await afterTheWait()

    expect(router.state.location.search).toBe('')
    expect(box).toHaveValue('')
  })

  it('shows the search from a shared link', async () => {
    openList('/tasks?search=invoice', onePage)

    expect(await screen.findByRole('searchbox', { name: 'Search titles' })).toHaveValue('invoice')
  })
})

describe('a shared link with invalid filters', () => {
  it('says which were ignored, until the next change rewrites the URL', async () => {
    const { router } = openList('/tasks?status=nope&page=x&search=invoice', onePage)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Some filters in this link weren't valid")
    expect(alert).toHaveTextContent('These were ignored: Status, Page.')

    await userEvent.click(screen.getByRole('combobox', { name: 'Order' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Newest first' }))

    expect(router.state.location.search).toBe('?search=invoice&ordering=-created_at')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
