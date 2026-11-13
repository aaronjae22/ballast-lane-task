import { z } from 'zod'
import type { components } from '../../api/generated/schema'

// The title rule here mirrors the domain's (ADR 0012, backend/tasks/domain/task.py) for display
// and early feedback only (ADR 0018). The API decides: its 400 still lands on the form's fields.
// Changing the rule means changing both copies and both sets of tests.

export type TaskCreateRequest = components['schemas']['TaskCreateRequest']

const titleMaxLength = 200

function isValidTitle(title: string): boolean {
  // Code points, as Python's len() counts them: .length would count a 😀 as two.
  const length = Array.from(title.trim()).length
  return length >= 1 && length <= titleMaxLength
}

/**
 * The create form's fields. Only the title is checked: a due date in the past depends on the
 * server's "today", and whether an assignee is still active on the server's data (ADR 0018).
 */
export const taskFormSchema = z.object({
  title: z.string().refine(isValidTitle, `Must be 1 to ${String(titleMaxLength)} characters.`),
  description: z.string(),
  /** A plain day, YYYY-MM-DD, as the date picker gives it, or null for none. */
  due_date: z.string().nullable(),
  /** An id from /api/users/, or null for unassigned. */
  assignee_id: z.number().nullable(),
})

export type TaskFormValues = z.infer<typeof taskFormSchema>

export const emptyTaskForm: TaskFormValues = {
  title: '',
  description: '',
  due_date: null,
  assignee_id: null,
}

/** The POST /api/tasks/ body. The description is sent as typed: the API keeps its spaces. */
export function toCreateRequest(values: TaskFormValues): TaskCreateRequest {
  return {
    title: values.title.trim(),
    description: values.description,
    due_date: values.due_date,
    assignee_id: values.assignee_id,
  }
}
