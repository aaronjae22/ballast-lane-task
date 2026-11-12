import { createContext } from 'react'
import type { ApiClient } from '../api/client'
import type { AuthStatus, Session } from './session'

export interface AuthContextValue {
  status: AuthStatus
  login: Session['login']
  logout(): Promise<void>
  /** For the "can't reach the server" screen. */
  retryRestore(): void
  /** The client every query hook uses: it carries the token and recovers from a 401. */
  api: ApiClient
}

export const AuthContext = createContext<AuthContextValue | null>(null)
