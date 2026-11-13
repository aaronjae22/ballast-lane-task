import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse, type JsonBodyType } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../queryClient'
import { apiUrl } from '../../test/api'
import { refreshAnswers } from '../../test/handlers'
import { createTestQueryClient } from '../../test/queryClient'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, createTask, getTask, held } from '../../test/tasks'

const created = aTask({ id: 31, title: 'Write the report' })

function openCreate(
  answers: Parameters<typeof createTask> = [created],
  queryClient = createTestQueryClient(),
) {
  const create = createTask(...answers)
  // After creating, the page opens the new task, which loads it.
  server.use(refreshAnswers('alice-token').handler, create.handler, getTask(created).handler)
  return { ...renderApp({ path: '/tasks/new', queryClient }), create }
}

async function typeTitle(title: string) {
  await userEvent.type(await screen.findByRole('textbox', { name: 'Title' }), title)
}

async function submit() {
  await userEvent.click(screen.getByRole('button', { name: 'Create task' }))
}

function answer(status: number, body: JsonBodyType, headers: Record<string, string> = {}) {
  return () => HttpResponse.json(body, { status, headers })
}

afterEach(() => {
  vi.useRealTimers()
})

describe('creating a task', () => {
  it('with a title only: sends no due date and no assignee, then opens the task', async () => {
    const { create, router } = openCreate()

    await typeTitle('  Write the report ')
    await submit()

    expect(await screen.findByText('Task created.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Write the report' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks/31')
    expect(create.bodies()).toEqual([
      { title: 'Write the report', description: '', due_date: null, assignee_id: null },
    ])
  })

  it('with a description, a due date and an assignee', async () => {
    // Only Date is faked, so the calendar opens on November 2026 and timers still run.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 12, 18, 30))
    const { create } = openCreate()

    await typeTitle('Write the report')
    await userEvent.type(screen.getByRole('textbox', { name: 'Description' }), 'Two pages.')
    await userEvent.click(screen.getByRole('button', { name: 'Due date' }))
    await userEvent.click(await screen.findByRole('button', { name: '20 November 2026' }))
    await userEvent.click(screen.getByRole('combobox', { name: 'Assignee' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Bob Smith' }))
    await submit()

    await screen.findByText('Task created.')
    expect(create.bodies()).toEqual([
      {
        title: 'Write the report',
        description: 'Two pages.',
        due_date: '2026-11-20',
        assignee_id: 2,
      },
    ])
  })

  it('marks the lists stale, so they show the new task', async () => {
    const queryClient = createTestQueryClient()
    const listKey = ['tasks', 'list', { page_size: 20 }]
    queryClient.setQueryData(listKey, aPage([]))
    openCreate([created], queryClient)

    await typeTitle('Write the report')
    await submit()

    await screen.findByText('Task created.')
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('sends one request however often the button is pressed while it runs', async () => {
    const response = held()
    const { create } = openCreate([
      async () => {
        await response.wait
        return HttpResponse.json(created, { status: 201 })
      },
    ])
    await typeTitle('Write the report')

    await submit()
    const button = screen.getByRole('button', { name: 'Create task' })
    expect(button).toBeDisabled()
    await userEvent.click(button)
    response.release()

    expect(await screen.findByText('Task created.')).toBeInTheDocument()
    expect(create.bodies()).toHaveLength(1)
  })

  it('Cancel goes back to the list', async () => {
    openCreate()

    expect(await screen.findByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/tasks')
  })
})

describe('checks before sending', () => {
  it.each([
    ['no title', ''],
    ['a title of spaces only', '   '],
    ['a title over 200 characters', 'x'.repeat(201)],
  ])('%s: says so on the field and sends nothing', async (_, title) => {
    const { create } = openCreate()
    if (title !== '') await typeTitle(title)
    else await screen.findByRole('textbox', { name: 'Title' })

    await submit()

    expect(await screen.findByRole('textbox', { name: 'Title' })).toHaveAccessibleDescription(
      'Must be 1 to 200 characters.',
    )
    expect(create.bodies()).toEqual([])
  })
})

describe("the API's answers", () => {
  it.each([
    ['title', 'textbox', 'Title', 'Must be 1 to 200 characters.'],
    ['due_date', 'button', 'Due date', "Can't be in the past."],
    ['assignee_id', 'combobox', 'Assignee', 'Must be an active user.'],
  ] as const)('a 400 on %s goes on its field', async (field, role, name, message) => {
    openCreate([answer(400, { [field]: [message] })])
    await typeTitle('Write the report')

    await submit()

    expect(await screen.findByRole(role, { name })).toHaveAccessibleDescription(message)
    expect(screen.queryByText('Task created.')).not.toBeInTheDocument()
  })

  it('a 400 on a key the form has no field for goes in an alert above it', async () => {
    openCreate([answer(400, { non_field_errors: ['Tasks are read-only today.'] })])
    await typeTitle('Write the report')

    await submit()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Some values weren't accepted")
    expect(alert).toHaveTextContent('Tasks are read-only today.')
  })

  it('a 429 says when to try again, and keeps what was typed', async () => {
    openCreate([answer(429, { detail: 'Request was throttled.' }, { 'Retry-After': '30' })])
    await typeTitle('Write the report')

    await submit()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Too many requests')
    expect(alert).toHaveTextContent('Try again in 30 seconds.')
    expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('Write the report')
  })

  it("no answer says the server can't be reached", async () => {
    openCreate([() => HttpResponse.error()])
    await typeTitle('Write the report')

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent("Can't reach the server")
  })

  it("a 5xx isn't retried, even by the app's query client: the task may have been created", async () => {
    const { create } = openCreate(
      [answer(503, { detail: 'Service unavailable.' })],
      createQueryClient(),
    )
    await typeTitle('Write the report')

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent("Can't reach the server")
    expect(create.bodies()).toHaveLength(1)
  })

  it('a second try clears the last error', async () => {
    openCreate([() => HttpResponse.error(), created])
    await typeTitle('Write the report')
    await submit()
    await screen.findByRole('alert')

    await submit()

    expect(await screen.findByText('Task created.')).toBeInTheDocument()
    expect(screen.queryByText("Can't reach the server")).not.toBeInTheDocument()
  })
})

describe('the assignee picker', () => {
  it('starts unassigned, and offers Unassigned and the active users', async () => {
    openCreate()
    const picker = await screen.findByRole('combobox', { name: 'Assignee' })

    expect(picker).toHaveValue('Unassigned')
    await userEvent.click(picker)
    expect((await screen.findAllByRole('option')).map((option) => option.textContent)).toEqual([
      'Unassigned',
      'Alice Johnson',
      'Bob Smith',
      'Carol Diaz',
    ])
  })

  // An option, because the Select's clear button is hidden from the keyboard and from screen
  // readers (as in the Assign dialog).
  it('a picked assignee can be undone with the Unassigned option', async () => {
    const { create } = openCreate()
    await typeTitle('Write the report')
    const picker = screen.getByRole('combobox', { name: 'Assignee' })

    await userEvent.click(picker)
    await userEvent.click(await screen.findByRole('option', { name: 'Bob Smith' }))
    await userEvent.click(picker)
    await userEvent.click(await screen.findByRole('option', { name: 'Unassigned' }))
    await submit()

    await screen.findByText('Task created.')
    expect(create.bodies()).toEqual([
      { title: 'Write the report', description: '', due_date: null, assignee_id: null },
    ])
  })

  it("says so when the users can't be loaded, and the task can still be created", async () => {
    server.use(http.get(apiUrl('/api/users/'), answer(500, { detail: 'Server error' })))
    const { create } = openCreate()

    expect(
      await screen.findByText("Couldn't load the users. You can assign the task later."),
    ).toBeVisible()
    expect(screen.getByRole('combobox', { name: 'Assignee' })).toBeDisabled()
    await typeTitle('Write the report')
    await submit()

    await screen.findByText('Task created.')
    expect(create.bodies()).toHaveLength(1)
  })
})
