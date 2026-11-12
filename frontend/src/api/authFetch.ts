import type { Session } from '../auth/session'

export interface AuthFetchOptions {
  session: Pick<Session, 'getAccessToken' | 'refresh' | 'generation'>
  /** Sends the request. Defaults to the global fetch, looked up when the request is sent. */
  fetch?: (request: Request) => Promise<Response>
}

/**
 * The fetch the API client sends every request through (ADR 0016). It adds the access token
 * as each request is sent. On a 401 it waits for the session's single-flight refresh and
 * retries once with the new token, unless the user logged out meanwhile. /api/auth/ reads only
 * the cookie, so those requests go out unchanged.
 */
export function createAuthFetch({
  session,
  fetch: send = (request: Request) => globalThis.fetch(request),
}: AuthFetchOptions): (request: Request) => Promise<Response> {
  return async (request) => {
    if (new URL(request.url).pathname.startsWith('/api/auth/')) return send(request)

    const startedIn = session.generation()
    const sentToken = session.getAccessToken()
    // Cloned before sending: a sent body can't be read again, and the retry must resend it.
    const retry = request.clone()
    const response = await send(withToken(request, sentToken))
    if (response.status !== 401 || session.generation() !== startedIn) return response

    // Another request may have refreshed while this one was out: then the new token is here
    // already, and another refresh would only rotate the cookie again.
    if (session.getAccessToken() === sentToken) {
      const outcome = await session.refresh()
      if (outcome !== 'refreshed' || session.generation() !== startedIn) return response
    }
    const token = session.getAccessToken()
    if (token === null) return response
    return send(withToken(retry, token))
  }
}

function withToken(request: Request, token: string | null): Request {
  const headers = new Headers(request.headers)
  if (token === null) headers.delete('Authorization')
  else headers.set('Authorization', `Bearer ${token}`)
  return new Request(request, { headers })
}
