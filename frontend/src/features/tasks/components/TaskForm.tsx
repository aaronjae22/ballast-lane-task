import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Group, Select, Stack, Textarea, TextInput } from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { describeError, fieldErrorsOf } from '../../../api/errorMessages'
import { useActiveUsers } from '../../users/hooks/useActiveUsers'
import { emptyTaskForm, taskFormSchema, type TaskFormValues } from '../schemas'

interface TaskFormProps {
  submitLabel: string
  /** Where Cancel goes. */
  cancelTo: string
  /** Sends the values; a rejection's field errors go on the fields, anything else above them. */
  onSubmit: (values: TaskFormValues) => Promise<unknown>
}

type Field = keyof TaskFormValues

function isField(key: string): key is Field {
  return key in emptyTaskForm
}

export function TaskForm({ submitLabel, cancelTo, onSubmit }: TaskFormProps) {
  const users = useActiveUsers()
  const [failure, setFailure] = useState<{ title: string; message: string } | null>(null)
  const {
    control,
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: emptyTaskForm,
  })

  const submit = handleSubmit(async (values) => {
    setFailure(null)
    try {
      await onSubmit(values)
    } catch (error) {
      setFailure(failureOf(error, setError))
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
        <Controller
          control={control}
          name="assignee_id"
          render={({ field }) => (
            <Select
              label="Assignee"
              placeholder="Unassigned"
              clearable
              searchable
              data={(users.data ?? []).map((user) => ({
                value: String(user.id),
                label: user.name,
              }))}
              value={field.value === null ? null : String(field.value)}
              onChange={(value) => {
                field.onChange(value === null ? null : Number(value))
              }}
              onBlur={field.onBlur}
              disabled={users.isError}
              description={
                users.isError
                  ? "Couldn't load the users. You can assign the task later."
                  : undefined
              }
              error={errors.assignee_id?.message}
            />
          )}
        />
        <Group justify="flex-end">
          <Button component={Link} to={cancelTo} variant="default">
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

// A 400's field errors go on their fields (ADR 0018). What's left, or any other error, is the
// alert's to say.
function failureOf(
  error: unknown,
  setError: (field: Field, error: { type: string; message: string }) => void,
): { title: string; message: string } | null {
  const fields = fieldErrorsOf(error)
  if (fields === null) return describeError(error)
  const others: string[] = []
  for (const [key, messages] of Object.entries(fields)) {
    if (isField(key)) setError(key, { type: 'server', message: messages.join(' ') })
    else others.push(...messages)
  }
  if (others.length === 0) return null
  return { title: "Some values weren't accepted", message: others.join(' ') }
}
