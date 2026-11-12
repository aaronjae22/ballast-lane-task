import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { apiUrl } from './api'
import { users } from './handlers'

// The fake API every test talks to. Tests add handlers with server.use(); a request that no
// handler matches fails the test (ADR 0016). The one default: every signed-in page shows the
// user in its header, so /api/users/me/ answers with alice unless a test says otherwise.
export const server = setupServer(
  http.get(apiUrl('/api/users/me/'), () => HttpResponse.json(users.alice)),
)
