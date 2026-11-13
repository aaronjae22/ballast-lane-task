import { describe, expect, it } from 'vitest'
import {
  emptyTaskForm,
  taskFormSchema,
  toCreateRequest,
  toUpdateRequest,
  type TaskFormValues,
} from './schemas'

function form(overrides: Partial<TaskFormValues>): TaskFormValues {
  return { ...emptyTaskForm, title: 'Write the report', ...overrides }
}

function titleErrors(title: string): string[] {
  const result = taskFormSchema.safeParse(form({ title }))
  return result.success ? [] : result.error.issues.map((issue) => issue.message)
}

// The same rule as the domain's (ADR 0012), mirrored for early feedback only (ADR 0018). The
// backend's test_task_create.py pins the same boundaries.
describe('the title', () => {
  it.each([
    ['one character', 'x'],
    ['200 characters', 'x'.repeat(200)],
    ['200 characters once the spaces around it are stripped', `  ${'x'.repeat(200)}\n`],
    // Python's len() counts code points; a string's length in JavaScript counts UTF-16 units.
    ['200 characters outside the Basic Multilingual Plane', '😀'.repeat(200)],
  ])('accepts %s', (_, title) => {
    expect(titleErrors(title)).toEqual([])
  })

  it.each([
    ['an empty title', ''],
    ['a title of spaces only', '   \t\n'],
    ['201 characters', 'x'.repeat(201)],
    ['201 characters outside the Basic Multilingual Plane', '😀'.repeat(201)],
  ])("rejects %s with the API's message", (_, title) => {
    expect(titleErrors(title)).toEqual(['Must be 1 to 200 characters.'])
  })
})

describe('the due date', () => {
  // "Today" is the server's, in its TIME_ZONE (ADR 0012), so only the API can say a day is past.
  it('accepts a day in the past, for the API to judge', () => {
    expect(taskFormSchema.safeParse(form({ due_date: '2000-01-01' })).success).toBe(true)
  })

  it('accepts no due date', () => {
    expect(taskFormSchema.safeParse(form({ due_date: null })).success).toBe(true)
  })
})

describe('the create request', () => {
  it('sends the title without the spaces around it, and the rest as entered', () => {
    const values = form({
      title: '  Write the report ',
      description: '  Two pages.\n',
      due_date: '2026-11-20',
      assignee_id: 2,
    })

    expect(toCreateRequest(values)).toEqual({
      title: 'Write the report',
      description: '  Two pages.\n',
      due_date: '2026-11-20',
      assignee_id: 2,
    })
  })

  it('sends null for no due date and no assignee', () => {
    expect(toCreateRequest(form({}))).toEqual({
      title: 'Write the report',
      description: '',
      due_date: null,
      assignee_id: null,
    })
  })
})

// Edit sends only what the user changed (ADR 0018): an overdue task's date isn't sent back
// unless it was changed, and the assignee has its own endpoint.
describe('the update request', () => {
  const edited = form({
    title: '  Write the final report ',
    description: 'Three pages.',
    due_date: '2026-11-05',
    assignee_id: 2,
  })

  it('holds only the changed fields, the title without the spaces around it', () => {
    expect(toUpdateRequest(edited, { title: true })).toEqual({ title: 'Write the final report' })
    expect(toUpdateRequest(edited, { description: true, due_date: true })).toEqual({
      description: 'Three pages.',
      due_date: '2026-11-05',
    })
  })

  it('sends null for a due date that was cleared', () => {
    expect(toUpdateRequest(form({ due_date: null }), { due_date: true })).toEqual({
      due_date: null,
    })
  })

  it('is empty when nothing changed', () => {
    expect(toUpdateRequest(edited, {})).toEqual({})
    expect(toUpdateRequest(edited, { title: false })).toEqual({})
  })

  it('never holds the assignee', () => {
    expect(toUpdateRequest(edited, { assignee_id: true })).toEqual({})
  })
})
