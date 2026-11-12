import { useQueryClient } from '@tanstack/react-query'
import {
  useCallback,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactElement,
  type ReactNode,
} from 'react'
import { AuthContext, type AuthContextValue } from './authContext'
import type { Auth } from './createAuth'

/**
 * Gives the app the session's status and actions (ADR 0016). It starts the silent refresh on
 * mount, and empties the query cache whenever the session becomes anonymous, so the next user
 * never sees the last one's data. Must sit inside a QueryClientProvider.
 */
export function AuthProvider({
  auth,
  children,
}: {
  auth: Auth
  children: ReactNode
}): ReactElement {
  const { session, api } = auth
  const subscribe = useCallback((listener: () => void) => session.subscribe(listener), [session])
  const getState = useCallback(() => session.getState(), [session])
  // Only the status reaches React: a token rotation changes nothing here, so renders nothing.
  const { status } = useSyncExternalStore(subscribe, getState)
  const queryClient = useQueryClient()

  // restore() is memoized, so StrictMode's second run of this effect sends no second request.
  useEffect(() => {
    void session.restore()
  }, [session])

  useEffect(() => {
    if (status !== 'anonymous') return
    // Cancelling aborts the queries' fetches through their AbortSignal.
    void queryClient.cancelQueries()
    queryClient.clear()
  }, [status, queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      login: (credentials) => session.login(credentials),
      logout: () => session.logout(),
      retryRestore: () => {
        void session.retryRestore()
      },
      api,
    }),
    [status, session, api],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
