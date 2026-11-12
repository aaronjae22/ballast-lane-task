// The signed-in session, outside React (ADR 0016). The access token lives only in this
// module's closure: never React state, never localStorage or sessionStorage. The refresh
// token is the backend's httpOnly cookie, which JavaScript never sees.

import type { ApiClient } from '../api/client'
import { ApiError } from '../api/errors'
import type { components } from '../api/generated/schema'

export type LoginRequest = components['schemas']['LoginRequest']

/** `restoring` until the first silent refresh answers, never `anonymous` before that. */
export type AuthStatus = 'restoring' | 'authenticated' | 'anonymous' | 'unavailable'

export interface SessionState {
  readonly status: AuthStatus
}

/**
 * How a refresh ended. `rejected`: there's no session (no cookie, or a cookie the backend
 * refused twice). `unavailable`: the backend couldn't answer (network error, 5xx or 429).
 */
export type RefreshOutcome = 'refreshed' | 'rejected' | 'unavailable'

/** Why a login failed, for the login form's message. */
export type LoginFailure = 'invalid' | 'throttled' | 'unavailable'

const loginMessages: Record<LoginFailure, string> = {
  invalid: 'Wrong username or password.',
  throttled: 'Too many login attempts.',
  unavailable: "Can't reach the server.",
}

export class LoginError extends Error {
  readonly kind: LoginFailure
  /** Seconds to wait, from Retry-After, when the login was throttled. */
  readonly retryAfter: number | null

  constructor(kind: LoginFailure, retryAfter: number | null = null) {
    super(loginMessages[kind])
    this.name = 'LoginError'
    this.kind = kind
    this.retryAfter = retryAfter
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
  /**
   * Throws LoginError. On success the status is `authenticated`, unless the user logged out
   * while the login was in flight: then its answer is discarded and its cookie revoked.
   */
  login(credentials: LoginRequest): Promise<void>
  /** Signs out locally whatever the backend answers, then the status is `anonymous`. */
  logout(): Promise<void>
  /**
   * The silent refresh on page load. Memoized for the session's lifetime: a second call (React
   * StrictMode runs effects twice) gets the same promise, not a second request. Sets the
   * status to `authenticated`, `anonymous` or `unavailable`.
   */
  restore(): Promise<RefreshOutcome>
  /** Tries the restore again after `unavailable`. The status is `restoring` meanwhile. */
  retryRestore(): Promise<RefreshOutcome>
  /**
   * A new access token from the refresh cookie. One at a time: callers that arrive while a
   * refresh is in flight share its result (ADR 0014). A 401 is retried once, because another
   * tab may have just rotated the cookie. `rejected` signs out; `unavailable` keeps the
   * session.
   */
  refresh(): Promise<RefreshOutcome>
}

export interface SessionOptions {
  /** A client for /api/auth/ only: no access token, no retry. */
  authClient: ApiClient
}

export function createSession({ authClient }: SessionOptions): Session {
  let state: SessionState = { status: 'restoring' }
  let accessToken: string | null = null
  let generation = 0
  const listeners = new Set<() => void>()

  function setStatus(status: AuthStatus): void {
    if (state.status === status) return
    state = { status }
    for (const listener of listeners) listener()
  }

  // Blacklists the refresh cookie's token and clears the cookie. Errors are ignored: the
  // backend always answers 204 when it's reachable (ADR 0014).
  async function revokeRefreshCookie(): Promise<void> {
    try {
      await authClient.POST('/api/auth/logout/')
    } catch {
      // Unreachable: signed out on this page all the same.
    }
  }

  return {
    restore: () => Promise.reject(new Error('not implemented')),
    retryRestore: () => Promise.reject(new Error('not implemented')),
    refresh: () => Promise.reject(new Error('not implemented')),

    getState: () => state,

    subscribe(listener) {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },

    getAccessToken: () => accessToken,

    generation: () => generation,

    async login(credentials) {
      const startedIn = generation
      let result
      try {
        result = await authClient.POST('/api/auth/token/', { body: credentials })
      } catch {
        // fetch rejects only when no response came back: the server is down or unreachable.
        throw new LoginError('unavailable')
      }
      if (result.data && generation !== startedIn) {
        // The user logged out while this login was in flight. Its answer set a new refresh
        // cookie after logout cleared the old one, so revoke that too, or a reload would
        // sign the user back in. The session stays signed out.
        await revokeRefreshCookie()
        return
      }
      if (result.data) {
        accessToken = result.data.access
        setStatus('authenticated')
        return
      }
      const error = new ApiError(result.response, result.error)
      // 400 is a missing field, which the form checks first; to the user it's the same.
      if (error.status === 401 || error.status === 400) throw new LoginError('invalid')
      if (error.status === 429) throw new LoginError('throttled', error.retryAfter)
      throw new LoginError('unavailable')
    },

    async logout() {
      // Signed out locally first: requests from now on carry no token, and anything that
      // started before can tell from the generation (ADR 0016).
      generation += 1
      accessToken = null
      await revokeRefreshCookie()
      setStatus('anonymous')
    },
  }
}
