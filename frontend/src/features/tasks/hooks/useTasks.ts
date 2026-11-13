import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query'
import { unwrap } from '../../../api/errors'
import type { components } from '../../../api/generated/schema'
import { useApi, useAuth } from '../../../auth/useAuth'
import { toApiQuery, type TaskFilters } from '../filters'
import { taskKeys } from './keys'

export type Task = components['schemas']['Task']
export type TaskPage = components['schemas']['PaginatedTaskList']

/**
 * A page of the tasks the user can see, for some filters. While another page or filter loads,
 * it keeps returning the last page, so the list doesn't empty and jump (isPlaceholderData).
 */
export function useTasks(filters: TaskFilters): UseQueryResult<TaskPage> {
  const api = useApi()
  const { status } = useAuth()
  const query = toApiQuery(filters)
  return useQuery({
    queryKey: taskKeys.list(query),
    queryFn: async ({ signal }) =>
      unwrap(await api.GET('/api/tasks/', { params: { query }, signal })),
    placeholderData: keepPreviousData,
    enabled: status === 'authenticated',
  })
}

/** One task, GET /api/tasks/{id}/. A task the user can't see is a 404, like a deleted one. */
export function useTask(id: number): UseQueryResult<Task> {
  const api = useApi()
  const { status } = useAuth()
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: async ({ signal }) =>
      unwrap<Task>(await api.GET('/api/tasks/{id}/', { params: { path: { id } }, signal })),
    enabled: status === 'authenticated',
  })
}
