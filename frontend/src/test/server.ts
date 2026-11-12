import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { apiUrl, type Schemas } from './api'
import { activeUsers, users } from './handlers'

// The fake API every test talks to. Tests add handlers with server.use(); a request that no
// handler matches fails the test (ADR 0016). Three defaults, because every signed-in page asks
// for them: /api/users/me/ answers with alice, for the header, /api/tasks/ with an empty page,
// because a signed-in user lands on the task list, and /api/users/ with the test users, for the
// list's assignee filter.
export const server = setupServer(
  activeUsers(),
  http.get(apiUrl('/api/users/me/'), () => HttpResponse.json(users.alice)),
  http.get(apiUrl('/api/tasks/'), () =>
    HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } satisfies Schemas['PaginatedTaskList']),
  ),
)
