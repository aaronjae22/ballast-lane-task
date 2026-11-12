import type { ReactElement } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { FullPageError } from '../components/FullPageError'
import { FullPageLoader } from '../components/FullPageLoader'
import { useAuth } from './useAuth'

/**
 * Guards the signed-in routes. While the session is restoring it shows a loader, never the
 * login page; when the server can't be reached, an error with a retry; when anonymous, a
 * redirect to /login that remembers where the user was going.
 */
export function RequireAuth(): ReactElement {
  const { status, retryRestore } = useAuth()
  const location = useLocation()

  if (status === 'restoring') return <FullPageLoader />
  if (status === 'unavailable') {
    return (
      <FullPageError
        title="Can't reach the server"
        message="Check your connection, then try again."
        actionLabel="Try again"
        onAction={retryRestore}
      />
    )
  }
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}
