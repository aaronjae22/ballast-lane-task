import type { CurrentUser } from '../users/hooks/useCurrentUser'
import type { Task } from './hooks/useTasks'

/** The rows of the permission matrix. Start, complete and reopen share one rule. */
export type Action = 'view' | 'edit' | 'assign' | 'change_status' | 'delete'

export function can(
  _user: Pick<CurrentUser, 'id' | 'is_admin'> | undefined,
  _task: Pick<Task, 'owner' | 'assignee'>,
  _action: Action,
): boolean {
  throw new Error('not implemented')
}
