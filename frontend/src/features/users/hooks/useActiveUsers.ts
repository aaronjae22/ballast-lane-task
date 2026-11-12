import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { unwrap } from '../../../api/errors'
import type { components } from '../../../api/generated/schema'
import { useApi, useAuth } from '../../../auth/useAuth'

export type UserSummary = components['schemas']['UserSummary']

export const activeUsersKey = ['users', 'active'] as const

/**
 * The active users from /api/users/, for the assignee pickers and filter. The team is small
 * and changes rarely, so one fetch serves every picker for five minutes.
 */
export function useActiveUsers(): UseQueryResult<UserSummary[]> {
  const api = useApi()
  const { status } = useAuth()
  return useQuery({
    queryKey: activeUsersKey,
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/users/', { signal })),
    staleTime: 5 * 60 * 1000,
    enabled: status === 'authenticated',
  })
}
