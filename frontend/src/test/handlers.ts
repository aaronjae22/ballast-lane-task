import { http, HttpResponse } from 'msw'
import { apiUrl, type Schemas } from './api'

// MSW handlers for the auth endpoints, in the shapes ADR 0014 fixes. Each test picks the
// answers it needs with server.use(...).

export function loginSucceeds(access = 'access-1') {
  return http.post(apiUrl('/api/auth/token/'), () =>
    HttpResponse.json({ access } satisfies Schemas['AccessToken']),
  )
}

export function loginFails(status: number, headers: Record<string, string> = {}) {
  return http.post(apiUrl('/api/auth/token/'), () =>
    HttpResponse.json(
      { detail: 'No active account found with the given credentials' } satisfies Schemas['Error'],
      { status, headers },
    ),
  )
}

export function loginUnreachable() {
  return http.post(apiUrl('/api/auth/token/'), () => HttpResponse.error())
}

export function logoutSucceeds() {
  return http.post(apiUrl('/api/auth/logout/'), () => new HttpResponse(null, { status: 204 }))
}

export function logoutUnreachable() {
  return http.post(apiUrl('/api/auth/logout/'), () => HttpResponse.error())
}

/**
 * Answers refreshes in order, one answer per request: a number is that status with no body
 * (204) or an error body, a string is a 200 with that access token, and 'unreachable' is a
 * network error. The last answer repeats. `count()` is the number of refreshes received.
 */
export function refreshAnswers(...answers: (number | string)[]) {
  let received = 0
  const handler = http.post(apiUrl('/api/auth/token/refresh/'), () => {
    const answer = answers[Math.min(received, answers.length - 1)]
    received += 1
    if (answer === 'unreachable') return HttpResponse.error()
    if (typeof answer === 'string') {
      return HttpResponse.json({ access: answer } satisfies Schemas['AccessToken'])
    }
    if (answer === 204) return new HttpResponse(null, { status: 204 })
    return HttpResponse.json({ detail: 'Token is invalid' } satisfies Schemas['Error'], {
      status: answer,
    })
  })
  return { handler, count: () => received }
}

export const users = {
  alice: { id: 1, username: 'alice', name: 'Alice Johnson', is_admin: false },
  bob: { id: 2, username: 'bob', name: 'Bob Smith', is_admin: false },
  carol: { id: 3, username: 'carol', name: 'Carol Diaz', is_admin: false },
} satisfies Record<string, Schemas['CurrentUser']>

/** /api/users/: the active users as {id, name}, ordered by username as the API orders them. */
export function activeUsers(list = Object.values(users)) {
  return http.get(apiUrl('/api/users/'), () =>
    HttpResponse.json(
      list.map(({ id, name }) => ({ id, name })) satisfies Schemas['UserSummary'][],
    ),
  )
}

/**
 * A small fake of the real auth flow for whole-app tests: logging in as `alice` or `bob`
 * gives the token `<username>-token`, and /api/users/me/ answers with the user that token
 * belongs to, or 401.
 */
export function signedInAs() {
  return [
    http.post(apiUrl('/api/auth/token/'), async ({ request }) => {
      const { username } = (await request.json()) as Schemas['LoginRequest']
      return HttpResponse.json({ access: `${username}-token` } satisfies Schemas['AccessToken'])
    }),
    http.get(apiUrl('/api/users/me/'), ({ request }) => {
      const header = request.headers.get('Authorization')
      const user = Object.values(users).find((u) => header === `Bearer ${u.username}-token`)
      if (user) return HttpResponse.json(user)
      return HttpResponse.json({ detail: 'Token is invalid' } satisfies Schemas['Error'], {
        status: 401,
      })
    }),
  ]
}
