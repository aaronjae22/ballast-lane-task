import { z } from 'zod'
import type { components } from '../../api/generated/schema'

export type TaskCreateRequest = components['schemas']['TaskCreateRequest']

export const taskFormSchema = z.object({
  title: z.string(),
  description: z.string(),
  due_date: z.string().nullable(),
  assignee_id: z.number().nullable(),
})

export type TaskFormValues = z.infer<typeof taskFormSchema>

export const emptyTaskForm: TaskFormValues = {
  title: '',
  description: '',
  due_date: null,
  assignee_id: null,
}

export function toCreateRequest(_values: TaskFormValues): TaskCreateRequest {
  throw new Error('not implemented')
}
