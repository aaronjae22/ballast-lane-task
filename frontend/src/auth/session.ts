// The signed-in session, outside React (ADR 0016). The access token lives only in this
// module's closure: never React state, never localStorage or sessionStorage. The refresh
// token is the backend's httpOnly cookie, which JavaScript never sees.

import type { ApiClient } from '../api/client'
import type { components } from '../api/generated/schema'

export type LoginRequest = components['schemas']['LoginRequest']

/** `restoring` until the first silent refresh answers, never `anonymous` before that. */
export type AuthStatus = 'restoring' | 'authenticated' | 'anonymous' | 'unavailable'

export interface SessionState {
  readonly status: AuthStatus
}

/** Why a login failed, for the login form's message. */
export type LoginFailure = 'invalid' | 'throttled' | 'unavailable'

export class LoginError extends Error {
  readonly kind: LoginFailure
  /** Seconds to wait, from Retry-After, when the login was throttled. */
  readonly retryAfter: number | null

  constructor(_kind: LoginFailure, _retryAfter: number | null = null) {
    super('not implemented')
    throw new Error('not implemented')
  }
}

export interface Session {
  /** The current state. The same object until the status changes (useSyncExternalStore). */
  getState(): SessionState
  /** Calls the listener after every status change. Returns the unsubscribe function. */
  subscribe(listener: () => void): () => void
  /** The access token for the next request, or null. Read per request, never cached. */
  getAccessToken(): string | null
  /** Changes at every logout, so work started before it can tell it's stale. */
  generation(): number
  /** Throws LoginError. On success the status is `authenticated`. */
  login(credentials: LoginRequest): Promise<void>
  /** Signs out locally whatever the backend answers, then the status is `anonymous`. */
  logout(): Promise<void>
}

export interface SessionOptions {
  /** A client for /api/auth/ only: no access token, no retry. */
  authClient: ApiClient
}

export function createSession(_options: SessionOptions): Session {
  throw new Error('not implemented')
}
