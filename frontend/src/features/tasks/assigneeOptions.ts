import type { UserSummary } from '../users/hooks/useActiveUsers'

// The assignee pickers' options, for the create form and the Assign dialog. Unassigned is an
// option of its own: the Select's clear button is hidden from the keyboard and from screen
// readers, so it can't be the only way back to no assignee.
const unassigned = 'unassigned'

/**
 * Unassigned, then the active users, then `current` if it isn't one of them: an assignee
 * deactivated since still shows (ADR 0018).
 */
export function assigneeOptions(
  people: readonly UserSummary[],
  current: UserSummary | null = null,
): { value: string; label: string }[] {
  const extra = current && !people.some((user) => user.id === current.id) ? [current] : []
  return [
    { value: unassigned, label: 'Unassigned' },
    ...[...people, ...extra].map((user) => ({ value: String(user.id), label: user.name })),
  ]
}

/** An assignee_id as the picker's value. */
export function toOptionValue(assigneeId: number | null): string {
  return assigneeId === null ? unassigned : String(assigneeId)
}

/** The picker's value as an assignee_id: null for Unassigned. */
export function fromOptionValue(value: string): number | null {
  return value === unassigned ? null : Number(value)
}
