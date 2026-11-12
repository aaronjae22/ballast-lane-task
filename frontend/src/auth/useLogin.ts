import type { UseMutationResult } from '@tanstack/react-query'
import type { LoginRequest } from './session'

/** Logs in through the session; a successful login makes the status `authenticated`. */
export function useLogin(): UseMutationResult<void, Error, LoginRequest> {
  throw new Error('not implemented')
}
