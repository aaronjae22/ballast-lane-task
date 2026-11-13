import type { CurrentUser } from '../users/hooks/useCurrentUser'
import type { Task } from './hooks/useTasks'

// This mirrors the permission matrix in spec section 3 (backend/tasks/domain/permissions.py),
// for display only (ADR 0018): it decides which actions a user is shown. The API decides what
// happens, and its 403 or 404 is still handled on every screen, because a task can change
// between the read and the write. Changing the matrix means changing both copies and both
// tests: the backend's permission-matrix test and permissions.test.ts.

/** The rows of the permission matrix. Start, complete and reopen share one rule. */
export type Action = 'view' | 'edit' | 'assign' | 'change_status' | 'delete'

// The owner and admins may take every action; the assignee only these.
const assigneeActions: ReadonlySet<Action> = new Set(['view', 'change_status'])

/**
 * Whether the user may take the action on the task. Before the signed-in user has loaded,
 * nothing is offered, so no button appears and then vanishes.
 */
export function can(
  user: Pick<CurrentUser, 'id' | 'is_admin'> | undefined,
  task: Pick<Task, 'owner' | 'assignee'>,
  action: Action,
): boolean {
  if (user === undefined) return false
  if (user.is_admin || user.id === task.owner.id) return true
  return user.id === task.assignee?.id && assigneeActions.has(action)
}

export type Transition = 'start' | 'complete' | 'reopen'

export function transitionsFrom(_status: Task['status']): Transition[] {
  throw new Error('not implemented')
}
