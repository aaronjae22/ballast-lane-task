import { useMutation, type UseMutationResult } from '@tanstack/react-query'
import type { LoginRequest } from './session'
import { useAuth } from './useAuth'

/** Logs in through the session; a successful login makes the status `authenticated`. */
export function useLogin(): UseMutationResult<void, Error, LoginRequest> {
  const { login } = useAuth()
  return useMutation({ mutationFn: login })
}
