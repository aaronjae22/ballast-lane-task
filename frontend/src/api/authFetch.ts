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
export function createAuthFetch(
  _options: AuthFetchOptions,
): (request: Request) => Promise<Response> {
  throw new Error('not implemented')
}
