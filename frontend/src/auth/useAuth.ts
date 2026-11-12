import { use } from 'react'
import type { ApiClient } from '../api/client'
import { AuthContext, type AuthContextValue } from './authContext'

/** The session's status and actions. Throws outside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const value = use(AuthContext)
  if (value === null) throw new Error('useAuth must be used inside <AuthProvider>.')
  return value
}

/** The API client, for query hooks. */
export function useApi(): ApiClient {
  return useAuth().api
}
