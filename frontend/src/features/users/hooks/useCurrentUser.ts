import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { unwrap } from '../../../api/errors'
import type { components } from '../../../api/generated/schema'
import { useApi, useAuth } from '../../../auth/useAuth'

export type CurrentUser = components['schemas']['CurrentUser']

export const currentUserKey = ['users', 'me'] as const

/** The signed-in user from /api/users/me/. Runs only while the session is authenticated. */
export function useCurrentUser(): UseQueryResult<CurrentUser> {
  const api = useApi()
  const { status } = useAuth()
  return useQuery({
    queryKey: currentUserKey,
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/users/me/', { signal })),
    enabled: status === 'authenticated',
  })
}
