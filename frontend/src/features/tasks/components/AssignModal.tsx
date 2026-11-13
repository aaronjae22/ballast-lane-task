import { Alert, Button, Group, Modal, Select, Stack } from '@mantine/core'
import { useState } from 'react'
import { describeError, fieldErrorsOf, type ErrorDescription } from '../../../api/errorMessages'
import { notifySuccess } from '../../../components/notify'
import { useActiveUsers } from '../../users/hooks/useActiveUsers'
import { useAssignTask } from '../hooks/useTaskMutations'
import type { Task } from '../hooks/useTasks'

interface AssignModalProps {
  task: Task
  opened: boolean
  onClose: () => void
}

/** Assign, reassign or unassign a task (spec section 3). */
export function AssignModal({ task, opened, onClose }: AssignModalProps) {
  return (
    <Modal opened={opened} onClose={onClose} title="Assign task">
      {/* Mounted only while open, so each opening starts from the task's current assignee. */}
      {opened && <AssignForm task={task} onDone={onClose} />}
    </Modal>
  )
}

// An option of its own: the Select's clear button is hidden from the keyboard and from screen
// readers, so it can't be the only way to unassign.
const unassigned = 'unassigned'

function AssignForm({ task, onDone }: { task: Task; onDone: () => void }) {
  const users = useActiveUsers()
  const assign = useAssignTask(task.id)
  const current = task.assignee?.id ?? null
  const [value, setValue] = useState(current === null ? unassigned : String(current))
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [failure, setFailure] = useState<ErrorDescription | null>(null)

  // A current assignee deactivated since isn't in /api/users/, but still shows (ADR 0018).
  const people = users.data ?? []
  const options = [
    { value: unassigned, label: 'Unassigned' },
    ...[
      ...people,
      ...(task.assignee && !people.some((user) => user.id === task.assignee?.id)
        ? [task.assignee]
        : []),
    ].map((user) => ({ value: String(user.id), label: user.name })),
  ]

  async function submit() {
    const next = value === unassigned ? null : Number(value)
    if (next === current) {
      onDone()
      return
    }
    setFieldError(null)
    setFailure(null)
    try {
      const assigned = await assign.mutateAsync(next)
      notifySuccess(
        assigned.assignee ? `Assigned to ${assigned.assignee.name}.` : 'Task unassigned.',
      )
      onDone()
    } catch (error) {
      // The API's 400 for a user deactivated since the picker loaded goes on the field.
      const messages = fieldErrorsOf(error)?.assignee_id
      if (messages) setFieldError(messages.join(' '))
      else setFailure(describeError(error))
    }
  }

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      <Stack>
        {failure && (
          <Alert color="red" variant="light" title={failure.title}>
            {failure.message}
          </Alert>
        )}
        <Select
          label="Assignee"
          placeholder="Unassigned"
          data={options}
          value={value}
          onChange={(next) => {
            // Picking the selected option again would deselect it; the value stays.
            if (next !== null) setValue(next)
            setFieldError(null)
          }}
          allowDeselect={false}
          searchable
          error={fieldError}
          description={
            users.isError ? "Couldn't load the users. You can still unassign the task." : undefined
          }
          data-autofocus
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" loading={assign.isPending}>
            Save
          </Button>
        </Group>
      </Stack>
    </form>
  )
}
