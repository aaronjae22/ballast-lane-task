import type { UseQueryResult } from '@tanstack/react-query'
import type { components } from '../../../api/generated/schema'
import type { TaskFilters } from '../filters'

export type Task = components['schemas']['Task']
export type TaskPage = components['schemas']['PaginatedTaskList']

/** A page of the tasks the user can see, for some filters. */
export function useTasks(_filters: TaskFilters): UseQueryResult<TaskPage> {
  throw new Error('not implemented')
}
