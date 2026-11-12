import type { TaskListQuery } from '../filters'

/**
 * The query keys for tasks. Every list sits under lists(), so one invalidation refreshes them
 * all after a change (ADR 0018).
 */
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => ['tasks', 'list'] as const,
  list: (query: TaskListQuery) => ['tasks', 'list', query] as const,
  detail: (id: number) => ['tasks', 'detail', id] as const,
}
