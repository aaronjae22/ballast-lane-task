import { act, waitFor } from '@testing-library/react'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../../../api/errors'
import { refreshAnswers } from '../../../test/handlers'
import { renderRoute } from '../../../test/render'
import { server } from '../../../test/server'
import { aPage, aTask, held, listTasks } from '../../../test/tasks'
import { useTaskFilters, type TaskFiltersState } from './useTaskFilters'
import { useTasks } from './useTasks'

interface Seen {
  filters: TaskFiltersState
  tasks: ReturnType<typeof useTasks>
}

// Renders the two hooks the list page uses, and keeps what they returned last.
function renderList(path: string) {
  const seen: { latest: Seen | null } = { latest: null }
  function Probe({ onRender }: { onRender: (value: Seen) => void }) {
    const filters = useTaskFilters()
    const tasks = useTasks(filters.filters)
    onRender({ filters, tasks })
    return null
  }
  const app = renderRoute(
    <Probe
      onRender={(value) => {
        seen.latest = value
      }}
    />,
    { path },
  )
  const latest = (): Seen => {
    if (seen.latest === null) throw new Error('the hooks never rendered')
    return seen.latest
  }
  return { ...app, latest }
}

function signedIn() {
  server.use(refreshAnswers('alice-token').handler)
}

describe('useTaskFilters', () => {
  it('reads the filters from the URL, and says which values it ignored', () => {
    signedIn()
    server.use(listTasks(aPage([])).handler)

    const { latest } = renderList('/tasks?status=done&page=x')

    expect(latest().filters.filters.status).toEqual(['done'])
    expect(latest().filters.filters.page).toBe(1)
    expect(latest().filters.ignored).toEqual(['page'])
  })

  it('writes a change to the URL as a new history entry, back on page 1', async () => {
    signedIn()
    server.use(listTasks(aPage([])).handler)
    const { latest, router } = renderList('/tasks?status=done&page=3')

    act(() => {
      latest().filters.setFilters({ overdue: true })
    })

    expect(router.state.location.search).toBe('?status=done&overdue=true')
    expect(router.state.historyAction).toBe('PUSH')
    await act(() => router.navigate(-1))
    expect(router.state.location.search).toBe('?status=done&page=3')
    expect(latest().filters.filters.overdue).toBeNull()
  })

  it('replaces the history entry when asked to, as the search box does while typing', () => {
    signedIn()
    server.use(listTasks(aPage([])).handler)
    const { latest, router } = renderList('/tasks')

    act(() => {
      latest().filters.setFilters({ search: 'inv' }, { replace: true })
    })

    expect(router.state.location.search).toBe('?search=inv')
    expect(router.state.historyAction).toBe('REPLACE')
  })

  it('applies several changes at once, as Clear filters will', () => {
    signedIn()
    server.use(listTasks(aPage([])).handler)
    const { latest, router } = renderList('/tasks?search=old&page=2')

    act(() => {
      latest().filters.setFilters({ status: ['to_do'], assignee: 'me', search: '' })
    })

    expect(router.state.location.search).toBe('?status=to_do&assignee=me')
  })

  it('drops the invalid values from the URL on the next change', () => {
    signedIn()
    server.use(listTasks(aPage([])).handler)
    const { latest, router } = renderList('/tasks?status=nope&utm_source=mail')

    act(() => {
      latest().filters.setFilters({ overdue: false })
    })

    expect(router.state.location.search).toBe('?overdue=false')
  })
})

describe('useTasks', () => {
  it("sends the URL's filters to the API in the API's format", async () => {
    signedIn()
    const list = listTasks(aPage([aTask()]))
    server.use(list.handler)

    const { latest } = renderList(
      '/tasks?status=to_do&status=done&assignee=me&ordering=-due_date&page=2&overdue=yes',
    )

    await waitFor(() => {
      expect(latest().tasks.isSuccess).toBe(true)
    })
    expect(list.requests()).toHaveLength(1)
    const query = list.requests()[0]?.searchParams
    expect(query?.getAll('status')).toEqual(['to_do', 'done'])
    expect(query?.get('assignee')).toBe('me')
    expect(query?.get('ordering')).toBe('-due_date')
    expect(query?.get('page')).toBe('2')
    // The invalid overdue=yes never reaches the API.
    expect(query?.has('overdue')).toBe(false)
  })

  it('returns the page the API answered', async () => {
    signedIn()
    const task = aTask({ title: 'Send the October invoice' })
    server.use(listTasks(aPage([task], { count: 21 })).handler)

    const { latest } = renderList('/tasks')

    await waitFor(() => {
      expect(latest().tasks.data).toEqual(aPage([task], { count: 21 }))
    })
  })

  it('keeps showing the previous page while the next one loads', async () => {
    signedIn()
    const first = aPage([aTask({ title: 'On page 1' })], { count: 21 })
    const second = aPage([aTask({ title: 'On page 2' })], { count: 21 })
    const gate = held()
    server.use(
      listTasks(first, async () => {
        await gate.wait
        return HttpResponse.json(second)
      }).handler,
    )
    const { latest } = renderList('/tasks')
    await waitFor(() => {
      expect(latest().tasks.data).toEqual(first)
    })

    act(() => {
      latest().filters.setFilters({ page: 2 })
    })

    await waitFor(() => {
      expect(latest().tasks.isFetching).toBe(true)
    })
    expect(latest().tasks.data).toEqual(first)
    expect(latest().tasks.isPlaceholderData).toBe(true)
    gate.release()
    await waitFor(() => {
      expect(latest().tasks.data).toEqual(second)
    })
  })

  it('fails with the API error, for the error state to describe', async () => {
    signedIn()
    server.use(
      listTasks(() => HttpResponse.json({ detail: 'Invalid page.' }, { status: 404 })).handler,
    )

    const { latest } = renderList('/tasks?page=9')

    await waitFor(() => {
      expect(latest().tasks.error).toBeInstanceOf(ApiError)
    })
    expect((latest().tasks.error as ApiError).status).toBe(404)
  })
})
