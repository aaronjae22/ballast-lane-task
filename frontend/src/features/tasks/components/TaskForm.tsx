import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Group, Select, Stack, Textarea, TextInput } from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import { useState } from 'react'
import { Controller, useForm, type Control } from 'react-hook-form'
import { Link } from 'react-router'
import { describeError, fieldErrorsOf } from '../../../api/errorMessages'
import { useActiveUsers } from '../../users/hooks/useActiveUsers'
import { assigneeOptions, fromOptionValue, toOptionValue } from '../assigneeOptions'
import { emptyTaskForm, taskFormSchema, type ChangedFields, type TaskFormValues } from '../schemas'

interface TaskFormProps {
  submitLabel: string
  /** Where Cancel goes, and the location state it takes along. */
  cancelTo: string
  cancelState?: unknown
  /** The values the form starts with: empty to create, the task's own to edit. */
  defaultValues?: TaskFormValues
  /** Edit has no assignee field: assigning has its own endpoint (ADR 0004). */
  withAssignee?: boolean
  /**
   * Sends the values, with the fields the user changed. A rejection's field errors go on the
   * fields, anything else above them.
   */
  onSubmit: (values: TaskFormValues, changed: ChangedFields) => Promise<unknown>
}

type Field = keyof TaskFormValues

export function TaskForm({
  submitLabel,
  cancelTo,
  cancelState,
  defaultValues = emptyTaskForm,
  withAssignee = true,
  onSubmit,
}: TaskFormProps) {
  const [failure, setFailure] = useState<{ title: string; message: string } | null>(null)
  const {
    control,
    register,
    handleSubmit,
    setError,
    // dirtyFields is read here, during render: React Hook Form tracks only what's read.
    formState: { errors, isSubmitting, dirtyFields },
  } = useForm<TaskFormValues>({ resolver: zodResolver(taskFormSchema), defaultValues })
  // A field error for a field the form doesn't show would be invisible, so it goes above.
  const isShown = (key: string): key is Field =>
    key in emptyTaskForm && (withAssignee || key !== 'assignee_id')

  const submit = handleSubmit(async (values) => {
    setFailure(null)
    try {
      await onSubmit(values, dirtyFields)
    } catch (error) {
      setFailure(failureOf(error, isShown, setError))
    }
  })

  return (
    <form
      noValidate
      onSubmit={(event) => {
        void submit(event)
      }}
    >
      <Stack>
        {failure && (
          <Alert color="red" variant="light" title={failure.title}>
            {failure.message}
          </Alert>
        )}
        <TextInput
          label="Title"
          withAsterisk
          error={errors.title?.message}
          {...register('title')}
        />
        <Textarea
          label="Description"
          rows={4}
          error={errors.description?.message}
          {...register('description')}
        />
        <Controller
          control={control}
          name="due_date"
          render={({ field }) => (
            <DatePickerInput
              label="Due date"
              placeholder="No due date"
              valueFormat="MMM D, YYYY"
              clearable
              clearButtonProps={{ 'aria-label': 'Clear due date' }}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={errors.due_date?.message}
            />
          )}
        />
        {withAssignee && <AssigneeSelect control={control} error={errors.assignee_id?.message} />}
        <Group justify="flex-end">
          <Button component={Link} to={cancelTo} state={cancelState} variant="default">
            Cancel
          </Button>
          <Button type="submit" loading={isSubmitting}>
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </form>
  )
}

// Its own component, so only a form with the field loads the users.
function AssigneeSelect({
  control,
  error,
}: {
  control: Control<TaskFormValues>
  error: string | undefined
}) {
  const users = useActiveUsers()
  return (
    <Controller
      control={control}
      name="assignee_id"
      render={({ field }) => (
        <Select
          label="Assignee"
          searchable
          data={assigneeOptions(users.data ?? [])}
          value={toOptionValue(field.value)}
          onChange={(value) => {
            // Picking the selected option again would deselect it; the value stays.
            if (value !== null) field.onChange(fromOptionValue(value))
          }}
          allowDeselect={false}
          onBlur={field.onBlur}
          disabled={users.isError}
          description={
            users.isError ? "Couldn't load the users. You can assign the task later." : undefined
          }
          error={error}
        />
      )}
    />
  )
}

// A 400's field errors go on their fields (ADR 0018). What's left, or any other error, is the
// alert's to say.
function failureOf(
  error: unknown,
  isShown: (key: string) => key is Field,
  setError: (field: Field, error: { type: string; message: string }) => void,
): { title: string; message: string } | null {
  const fields = fieldErrorsOf(error)
  if (fields === null) return describeError(error)
  const others: string[] = []
  for (const [key, messages] of Object.entries(fields)) {
    if (isShown(key)) setError(key, { type: 'server', message: messages.join(' ') })
    else others.push(...messages)
  }
  if (others.length === 0) return null
  return { title: "Some values weren't accepted", message: others.join(' ') }
}
