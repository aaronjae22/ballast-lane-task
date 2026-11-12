import type { ReactElement } from 'react'

/**
 * Guards the signed-in routes. While the session is restoring it shows a loader, never the
 * login page; when the server can't be reached, an error with a retry; when anonymous, a
 * redirect to /login that remembers where the user was going.
 */
export function RequireAuth(): ReactElement {
  throw new Error('not implemented')
}
