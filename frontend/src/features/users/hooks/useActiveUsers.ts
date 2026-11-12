import type { UseQueryResult } from '@tanstack/react-query'
import type { components } from '../../../api/generated/schema'

export type UserSummary = components['schemas']['UserSummary']

export const activeUsersKey = ['users', 'active'] as const

/** The active users from /api/users/, for the assignee pickers and filter. */
export function useActiveUsers(): UseQueryResult<UserSummary[]> {
  throw new Error('not implemented')
}
