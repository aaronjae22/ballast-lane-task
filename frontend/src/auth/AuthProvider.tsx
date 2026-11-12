import type { ReactElement, ReactNode } from 'react'
import type { Auth } from './createAuth'

/**
 * Gives the app the session's status and actions (ADR 0016). It starts the silent refresh on
 * mount, and empties the query cache whenever the session becomes anonymous, so the next user
 * never sees the last one's data. Must sit inside a QueryClientProvider.
 */
export function AuthProvider(_props: { auth: Auth; children: ReactNode }): ReactElement {
  throw new Error('not implemented')
}
