import { createAuthFetch } from '../api/authFetch'
import { createApiClient, type ApiClient } from '../api/client'
import { createSession, type Session } from './session'

export interface Auth {
  session: Session
  /** The client for every API call: it carries the token and recovers from a 401 once. */
  api: ApiClient
}

/** The page's session and API client, wired together. Created once, before React renders. */
export function createAuth(options: { baseUrl?: string } = {}): Auth {
  // The session talks to /api/auth/ through a plain client: a refresh must never trigger the
  // 401 handling it is part of.
  const session = createSession({ authClient: createApiClient(options) })
  const api = createApiClient({ ...options, fetch: createAuthFetch({ session }) })
  return { session, api }
}
