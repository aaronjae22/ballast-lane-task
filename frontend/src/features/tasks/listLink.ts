import { useLocation } from 'react-router'

// "Back to tasks" returns to the list the user came from, with its filters, order and page.
// The list's search travels in the location state of the links from the list, and on through
// the task's pages: history state, not app state (spec section 8: the AuthProvider is the only
// client state).

/** The location state a link from the list carries: the list's search, such as "?status=done". */
export interface FromList {
  list: string
}

// History state can hold anything, so only a search is taken: never a path or another site.
function listOf(state: unknown): string | null {
  const list: unknown =
    typeof state === 'object' && state !== null && 'list' in state ? state.list : null
  return typeof list === 'string' && (list === '' || list.startsWith('?')) ? list : null
}

/** Where "Back to tasks" goes from a page with this location state. */
export function listPathFrom(state: unknown): string {
  return `/tasks${listOf(state) ?? ''}`
}

/**
 * The state for a link to one of a task's pages: on the list, the list's search; on a task's
 * pages, the list they were opened from, if any.
 */
export function useListState(): FromList | undefined {
  const location = useLocation()
  if (location.pathname === '/tasks') return { list: location.search }
  const list = listOf(location.state as unknown)
  return list === null ? undefined : { list }
}
