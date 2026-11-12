import type { TaskFilters } from '../filters'

export interface TaskFiltersState {
  filters: TaskFilters
  /** The parameters in the URL whose values weren't valid, and were left out. */
  ignored: (keyof TaskFilters)[]
  /**
   * Changes the filters in the URL. It adds a history entry, so Back undoes it, unless
   * `replace` is set (for typing in the search box).
   */
  setFilters: (change: Partial<TaskFilters>, options?: { replace?: boolean }) => void
}

/** The list's filters, read from and written to the URL's query (ADR 0018). */
export function useTaskFilters(): TaskFiltersState {
  throw new Error('not implemented')
}
