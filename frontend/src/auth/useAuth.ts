import type { ApiClient } from '../api/client'
import type { AuthContextValue } from './authContext'

/** The session's status and actions. Throws outside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  throw new Error('not implemented')
}

/** The API client, for query hooks. */
export function useApi(): ApiClient {
  throw new Error('not implemented')
}
