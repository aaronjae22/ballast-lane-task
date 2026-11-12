import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import {
  changeFilters,
  parseTaskFilters,
  toSearchParams,
  type ParsedFilters,
  type TaskFilters,
} from '../filters'

export interface TaskFiltersState extends ParsedFilters {
  /**
   * Changes the filters in the URL. It adds a history entry, so Back undoes it, unless
   * `replace` is set (for typing in the search box).
   */
  setFilters: (change: Partial<TaskFilters>, options?: { replace?: boolean }) => void
}

/** The list's filters, read from and written to the URL's query (ADR 0018). */
export function useTaskFilters(): TaskFiltersState {
  const [params, setParams] = useSearchParams()
  const parsed = useMemo(() => parseTaskFilters(params), [params])

  const setFilters = useCallback<TaskFiltersState['setFilters']>(
    (change, { replace = false } = {}) => {
      // From the URL as it is now, not as it was rendered: two changes in a row both count.
      // Rebuilding the query from parsed filters also drops the values that were ignored.
      setParams(
        (current) => toSearchParams(changeFilters(parseTaskFilters(current).filters, change)),
        {
          replace,
        },
      )
    },
    [setParams],
  )

  return { ...parsed, setFilters }
}
