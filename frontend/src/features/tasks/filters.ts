import type { components, operations } from '../../api/generated/schema'
import { isDay } from './dates'

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

/** How many tasks a page holds. The list sends it, so it can count the pages. */
export const pageSize = 0

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

// Workflow order, which is also the order the filter shows them in.
export const statuses: readonly Status[] = ['to_do', 'in_progress', 'done']
export const orderings: readonly Ordering[] = [
  'due_date',
  '-due_date',
  'created_at',
  '-created_at',
  'status',
  '-status',
]

/** The filters in a URL's query. Each parameter is checked on its own. */
export function parseTaskFilters(params: URLSearchParams): ParsedFilters {
  const ignored: (keyof TaskFilters)[] = []
  // An empty value means no filter, as it does for the API (ADR 0013).
  const read = <T>(name: keyof TaskFilters, parse: (value: string) => T | null): T | null => {
    const value = params.get(name)?.trim() ?? ''
    if (value === '') return null
    const parsed = parse(value)
    if (parsed === null) ignored.push(name)
    return parsed
  }

  const given = params
    .getAll('status')
    .map((value) => value.trim())
    .filter((value) => value !== '')
  const status = statuses.filter((s) => given.includes(s))
  if (given.some((value) => !(statuses as readonly string[]).includes(value))) {
    ignored.push('status')
  }

  return {
    filters: {
      status,
      due_after: read('due_after', (v) => (isDay(v) ? v : null)),
      due_before: read('due_before', (v) => (isDay(v) ? v : null)),
      overdue: read('overdue', (v) => (v === 'true' ? true : v === 'false' ? false : null)),
      assignee: read('assignee', (v) => (v === 'me' ? 'me' : positiveInteger(v))),
      search: read('search', (v) => v) ?? '',
      ordering: read('ordering', (v) => orderings.find((o) => o === v) ?? null),
      page: read('page', positiveInteger) ?? 1,
    },
    ignored,
  }
}

/** The URL query for some filters, leaving out the defaults. */
export function toSearchParams(filters: TaskFilters): URLSearchParams {
  const params = new URLSearchParams()
  for (const status of filters.status) params.append('status', status)
  for (const [name, value] of Object.entries(toApiQuery(filters))) {
    if (name !== 'status') params.set(name, String(value))
  }
  return params
}

/** The /api/tasks/ query for some filters. */
export function toApiQuery(filters: TaskFilters): TaskListQuery {
  const query: TaskListQuery = {}
  if (filters.status.length > 0) query.status = [...filters.status]
  if (filters.due_after !== null) query.due_after = filters.due_after
  if (filters.due_before !== null) query.due_before = filters.due_before
  if (filters.overdue !== null) query.overdue = filters.overdue ? 'true' : 'false'
  if (filters.assignee !== null) query.assignee = String(filters.assignee)
  if (filters.search !== '') query.search = filters.search
  if (filters.ordering !== null) query.ordering = [filters.ordering]
  if (filters.page > 1) query.page = filters.page
  return query
}

/** The filters after a change. Any change but the page itself goes back to page 1. */
export function changeFilters(filters: TaskFilters, change: Partial<TaskFilters>): TaskFilters {
  return { ...filters, page: 1, ...change }
}

// The API takes ids and pages as positive integers. Beyond JavaScript's safe range a number
// would be rounded into another one, so it's treated as invalid.
function positiveInteger(text: string): number | null {
  if (!/^[1-9]\d*$/.test(text)) return null
  const value = Number(text)
  return Number.isSafeInteger(value) ? value : null
}
