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
