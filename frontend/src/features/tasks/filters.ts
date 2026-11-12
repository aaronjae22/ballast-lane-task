import type { components, operations } from '../../api/generated/schema'

/** The query /api/tasks/ takes, from the generated schema. */
export type TaskListQuery = NonNullable<operations['tasks_list']['parameters']['query']>
export type Status = components['schemas']['StatusEnum']
export type Ordering = NonNullable<TaskListQuery['ordering']>[number]

/**
 * The list's filters, named as the API names them (ADR 0018), so the URL, the state and the
 * request are the same thing. Empty means "not filtered".
 */
export interface TaskFilters {
  status: Status[]
  due_after: string | null
  due_before: string | null
  overdue: boolean | null
  assignee: 'me' | number | null
  search: string
  ordering: Ordering | null
  page: number
}

export const noFilters: TaskFilters = {
  status: [],
  due_after: null,
  due_before: null,
  overdue: null,
  assignee: null,
  search: '',
  ordering: null,
  page: 1,
}

export interface ParsedFilters {
  filters: TaskFilters
  /** The parameters whose values weren't valid, and were left out. */
  ignored: (keyof TaskFilters)[]
}

/** The filters in a URL's query. Each parameter is checked on its own. */
export function parseTaskFilters(_params: URLSearchParams): ParsedFilters {
  throw new Error('not implemented')
}

/** The URL query for some filters, leaving out the defaults. */
export function toSearchParams(_filters: TaskFilters): URLSearchParams {
  throw new Error('not implemented')
}

/** The /api/tasks/ query for some filters. */
export function toApiQuery(_filters: TaskFilters): TaskListQuery {
  throw new Error('not implemented')
}

/** The filters after a change. Any change but the page itself goes back to page 1. */
export function changeFilters(_filters: TaskFilters, _change: Partial<TaskFilters>): TaskFilters {
  throw new Error('not implemented')
}
