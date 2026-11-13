import { Alert, Button, Group, Modal, Select, Stack } from '@mantine/core'
import { useState } from 'react'
import { describeError, fieldErrorsOf, type ErrorDescription } from '../../../api/errorMessages'
import { notifySuccess } from '../../../components/notify'
import { useActiveUsers } from '../../users/hooks/useActiveUsers'
import type { useAssignTask } from '../hooks/useTaskMutations'
import type { Task } from '../hooks/useTasks'
import { assigneeOptions, fromOptionValue, toOptionValue } from '../assigneeOptions'

type Assign = ReturnType<typeof useAssignTask>

interface AssignModalProps {
  task: Task
  opened: boolean
  onClose: () => void
  /**
   * The task's assign mutation, owned by TaskActions: its pending state outlives the form, so
   * the task's other actions wait for it too (ADR 0018).
   */
  assign: Assign
}

/** Assign, reassign or unassign a task (spec section 3). */
export function AssignModal({ task, opened, onClose, assign }: AssignModalProps) {
  // While a save runs, the dialog stays open: closing and reopening it would start a second
  // assignment, and the first to be sent could finish last and win.
  const saving = assign.isPending
  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (!saving) onClose()
      }}
      title="Assign task"
      closeOnClickOutside={!saving}
      closeOnEscape={!saving}
      withCloseButton={!saving}
      closeButtonProps={{ 'aria-label': 'Close' }}
    >
      {/* Mounted only while open, so each opening starts from the task's current assignee. */}
      {opened && <AssignForm task={task} assign={assign} onDone={onClose} />}
    </Modal>
  )
}

function AssignForm({ task, assign, onDone }: { task: Task; assign: Assign; onDone: () => void }) {
  const users = useActiveUsers()
  const current = task.assignee?.id ?? null
  const [value, setValue] = useState(toOptionValue(current))
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [failure, setFailure] = useState<ErrorDescription | null>(null)

  const options = assigneeOptions(users.data ?? [], task.assignee)

  async function submit() {
    const next = fromOptionValue(value)
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
          <Button variant="default" onClick={onDone} disabled={assign.isPending}>
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
