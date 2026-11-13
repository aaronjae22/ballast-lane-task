import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, type JsonBodyType } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import type { Schemas } from '../../test/api'
import { admin, currentUser, refreshAnswers, users } from '../../test/handlers'
import { onWideScreen } from '../../test/media'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import { aPage, aTask, changeStatus, getTask, held, listTasks, summaryOf } from '../../test/tasks'

// Start, complete and reopen (spec section 3), from the task page and the list's quick actions
// (spec section 8). Which buttons show is the frontend's copy of the rules (ADR 0018).

const todo = aTask({
  id: 7,
  title: 'Send the October invoice',
  status: 'to_do',
  owner: summaryOf(users.alice),
  assignee: summaryOf(users.bob),
})
const started = { ...todo, status: 'in_progress' as const }
const done = { ...todo, status: 'done' as const, completed_at: '2026-11-12T17:05:00Z' }

function openTask(
  task: Schemas['Task'],
  answers: Parameters<typeof changeStatus>,
  me: Schemas['CurrentUser'] = users.alice,
) {
  const status = changeStatus(...answers)
  const get = getTask(task)
  server.use(
    refreshAnswers('alice-token').handler,
    currentUser(me),
    get.handler,
    ...status.handlers,
  )
  return { ...renderApp({ path: '/tasks/7' }), status, get }
}

async function buttons() {
  await screen.findByRole('heading', { level: 1 })
  // Wait for the signed-in user, who decides which buttons show.
  await within(screen.getByRole('banner')).findByText(/Johnson|Smith|Admin/)
  return ['Start', 'Complete', 'Reopen'].filter((name) => screen.queryByRole('button', { name }))
}

function answer(status: number, body: JsonBodyType, headers: Record<string, string> = {}) {
  return () => HttpResponse.json(body, { status, headers })
}

describe('which transitions a task offers', () => {
  it.each([
    ['to do', ['Start', 'Complete'], todo],
    ['in progress', ['Complete'], started],
    ['done', ['Reopen'], done],
  ])('%s: %j', async (_, expected, task) => {
    openTask(task, [task])

    expect(await buttons()).toEqual(expected)
  })

  it.each([
    ['the assignee', users.bob],
    ['an admin', admin],
  ])('%s may change the status too (spec section 3)', async (_, me) => {
    openTask(todo, [started], me)

    expect(await buttons()).toEqual(['Start', 'Complete'])
  })
})

describe('changing the status on the task page', () => {
  it.each([
    ['Start', todo, started, 'start', 'Task started.', 'In progress'],
    ['Complete', todo, done, 'complete', 'Task completed.', 'Done'],
    ['Reopen', done, todo, 'reopen', 'Task reopened.', 'To do'],
  ] as const)(
    '%s asks the API, says so, and shows the new status',
    async (button, before, after, call, message, status) => {
      const { status: requests } = openTask(before, [after])

      await userEvent.click(await screen.findByRole('button', { name: button }))

      expect(await screen.findByText(message)).toBeInTheDocument()
      expect(requests.calls()).toEqual([`7/${call}`])
      expect(await screen.findByText(status, { selector: '.mantine-Badge-label' })).toBeVisible()
    },
  )

  it("while one runs, its button is busy and the task's other actions are disabled", async () => {
    const response = held()
    openTask(todo, [
      async () => {
        await response.wait
        return HttpResponse.json(started)
      },
    ])
    await buttons()

    await userEvent.click(screen.getByRole('button', { name: 'Start' }))

    expect(screen.getByRole('button', { name: 'Start' })).toHaveAttribute('data-loading', 'true')
    expect(screen.getByRole('button', { name: 'Complete' })).toBeDisabled()
    response.release()
    expect(await screen.findByText('Task started.')).toBeInTheDocument()
  })
})

describe("the API's refusals", () => {
  it('a 409 from a stale button says the status changed, and refetches the task', async () => {
    const { get } = openTask(todo, [
      answer(409, { detail: "Can't start a task whose status is done." }),
    ])
    await buttons()

    await userEvent.click(screen.getByRole('button', { name: 'Start' }))

    expect(await screen.findByText("The task's status changed")).toBeInTheDocument()
    expect(screen.getByText("Can't start a task whose status is done.")).toBeInTheDocument()
    expect(get.ids()).toEqual(['7', '7'])
  })

  it.each([
    [403, { detail: "You can't change this task." }, 'Not allowed'],
    [404, { detail: 'Not found.' }, 'Task not found'],
    [429, { detail: 'Request was throttled.' }, 'Too many requests'],
  ] as const)('a %i is reported', async (status, body, title) => {
    openTask(todo, [answer(status, body, { 'Retry-After': '30' })])
    await buttons()

    await userEvent.click(screen.getByRole('button', { name: 'Start' }))

    expect((await screen.findAllByText(title)).length).toBeGreaterThan(0)
  })
})

describe('quick actions in the list', () => {
  let restore: (() => void) | null = null
  afterEach(() => {
    restore?.()
    restore = null
  })

  function openList() {
    const status = changeStatus(done)
    const list = listTasks(aPage([todo]), aPage([done]))
    server.use(refreshAnswers('alice-token').handler, list.handler, ...status.handlers)
    renderApp({ path: '/tasks' })
    return { status, list }
  }

  it("a card's Complete completes that task, and the list refetches", async () => {
    const { status, list } = openList()
    const card = within(await screen.findByRole('listitem'))

    await userEvent.click(await card.findByRole('button', { name: 'Complete' }))

    expect(await screen.findByText('Task completed.')).toBeInTheDocument()
    expect(status.calls()).toEqual(['7/complete'])
    expect(
      await within(await screen.findByRole('listitem')).findByRole('button', { name: 'Reopen' }),
    ).toBeInTheDocument()
    expect(list.requests()).toHaveLength(2)
  })

  it("a table row's Start starts that task", async () => {
    restore = onWideScreen()
    const { status } = openList()
    const row = within((await screen.findAllByRole('row'))[1] ?? document.body)

    await userEvent.click(await row.findByRole('button', { name: 'Start' }))

    expect(await screen.findByText('Task started.')).toBeInTheDocument()
    expect(status.calls()).toEqual(['7/start'])
  })
})
