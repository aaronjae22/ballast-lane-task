import type { ApiClient } from '../api/client'
import type { Session } from './session'

export interface Auth {
  session: Session
  /** The client for every API call: it carries the token and recovers from a 401 once. */
  api: ApiClient
}

/** The page's session and API client, wired together. Created once, before React renders. */
export function createAuth(_options: { baseUrl?: string } = {}): Auth {
  throw new Error('not implemented')
}
