import { createContext } from 'react'
import type { ApiClient } from '../api/client'
import type { AuthStatus, LoginRequest } from './session'

// The actions are function properties, not methods: they don't use `this`, so components can
// destructure them (const { logout } = useAuth()) safely.
export interface AuthContextValue {
  status: AuthStatus
  /** Throws LoginError (see session.ts). */
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  /** For the "can't reach the server" screen. */
  retryRestore: () => void
  /** The client every query hook uses: it carries the token and recovers from a 401. */
  api: ApiClient
}

export const AuthContext = createContext<AuthContextValue | null>(null)
