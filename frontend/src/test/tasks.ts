import { http, HttpResponse } from 'msw'
import { apiUrl, type Schemas } from './api'
import { users } from './handlers'

// Typed task fixtures and MSW handlers. A field the API drops or renames fails tsc here.

type Task = Schemas['Task']
type TaskPage = Schemas['PaginatedTaskList']
type Answer = TaskPage | (() => Response | Promise<Response>)

let nextId = 1

/** A user as a task shows them: {id, name}. */
export function summaryOf(user: { id: number; name: string }): Schemas['UserSummary'] {
  return { id: user.id, name: user.name }
}

/** A to-do task owned by alice, unassigned and without a due date, unless overridden. */
export function aTask(overrides: Partial<Task> = {}): Task {
  const id = overrides.id ?? nextId++
  return {
    id,
    title: `Task ${String(id)}`,
    description: '',
    status: 'to_do',
    due_date: null,
    is_overdue: false,
    owner: summaryOf(users.alice),
    assignee: null,
    completed_at: null,
    created_at: '2026-11-01T09:00:00Z',
    updated_at: '2026-11-01T09:00:00Z',
    ...overrides,
  }
}

/** One page of the list, with the count of every page unless overridden. */
export function aPage(results: Task[], overrides: Partial<TaskPage> = {}): TaskPage {
  return { count: results.length, next: null, previous: null, results, ...overrides }
}

/**
 * Answers GET /api/tasks/ in order, one answer per request; the last repeats. An answer is a
 * page, or a function for anything else (an error, a held response). `requests()` are the
 * URLs received, to check the query each one sent.
 */
export function listTasks(...answers: Answer[]) {
  const requests: URL[] = []
  const handler = http.get(apiUrl('/api/tasks/'), async ({ request }) => {
    const answer = answers[Math.min(requests.length, answers.length - 1)] ?? aPage([])
    requests.push(new URL(request.url))
    return typeof answer === 'function' ? answer() : HttpResponse.json(answer)
  })
  return { handler, requests: () => requests }
}

/**
 * Answers POST /api/tasks/ in order, one answer per request; the last repeats. An answer is the
 * created task (a 201), or a function for anything else. `bodies()` are the JSON bodies received.
 */
export function createTask(...answers: (Task | (() => Response | Promise<Response>))[]) {
  const bodies: unknown[] = []
  const handler = http.post(apiUrl('/api/tasks/'), async ({ request }) => {
    const answer = answers[Math.min(bodies.length, answers.length - 1)] ?? aTask()
    bodies.push(await request.json())
    return typeof answer === 'function' ? answer() : HttpResponse.json(answer, { status: 201 })
  })
  return { handler, bodies: () => bodies }
}

/**
 * Answers GET /api/tasks/{id}/ in order, one answer per request; the last repeats. An answer is
 * the task, or a function for anything else. `ids()` are the ids requested.
 */
export function getTask(...answers: (Task | (() => Response | Promise<Response>))[]) {
  const ids: string[] = []
  const handler = http.get(apiUrl('/api/tasks/{id}/'), ({ params }) => {
    const answer = answers[Math.min(ids.length, answers.length - 1)] ?? aTask()
    ids.push(String(params.id))
    return typeof answer === 'function' ? answer() : HttpResponse.json(answer)
  })
  return { handler, ids: () => ids }
}

/**
 * Answers PATCH /api/tasks/{id}/ in order, one answer per request; the last repeats. An answer
 * is the updated task, or a function for anything else. `bodies()` are the JSON bodies received.
 */
export function updateTask(...answers: (Task | (() => Response | Promise<Response>))[]) {
  const bodies: unknown[] = []
  const handler = http.patch(apiUrl('/api/tasks/{id}/'), async ({ request }) => {
    const answer = answers[Math.min(bodies.length, answers.length - 1)] ?? aTask()
    bodies.push(await request.json())
    return typeof answer === 'function' ? answer() : HttpResponse.json(answer)
  })
  return { handler, bodies: () => bodies }
}

/**
 * Answers POST /api/tasks/{id}/start/, /complete/ and /reopen/ in order, one answer per
 * request; the last repeats. An answer is the changed task, or a function for anything else.
 * `calls()` are what was asked, as "7/start".
 */
export function changeStatus(...answers: (Task | (() => Response | Promise<Response>))[]) {
  const calls: string[] = []
  const handlers = (['start', 'complete', 'reopen'] as const).map((action) =>
    http.post(apiUrl(`/api/tasks/{id}/${action}/` as const), ({ params }) => {
      const answer = answers[Math.min(calls.length, answers.length - 1)] ?? aTask()
      calls.push(`${String(params.id)}/${action}`)
      return typeof answer === 'function' ? answer() : HttpResponse.json(answer)
    }),
  )
  return { handlers, calls: () => calls }
}

/**
 * Answers POST /api/tasks/{id}/assign/ in order, one answer per request; the last repeats. An
 * answer is the task as assigned, or a function for anything else. `bodies()` are the JSON
 * bodies received.
 */
export function assignTask(...answers: (Task | (() => Response | Promise<Response>))[]) {
  const bodies: unknown[] = []
  const handler = http.post(apiUrl('/api/tasks/{id}/assign/'), async ({ request }) => {
    const answer = answers[Math.min(bodies.length, answers.length - 1)] ?? aTask()
    bodies.push(await request.json())
    return typeof answer === 'function' ? answer() : HttpResponse.json(answer)
  })
  return { handler, bodies: () => bodies }
}

/** A promise a handler can wait on, and the function that lets it go. */
export function held(): { wait: Promise<void>; release: () => void } {
  let release: () => void = () => undefined
  const wait = new Promise<void>((resolve) => {
    release = resolve
  })
  return { wait, release }
}
