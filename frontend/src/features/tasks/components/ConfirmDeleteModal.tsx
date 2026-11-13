import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core'
import { useState } from 'react'
import { describeError, type ErrorDescription } from '../../../api/errorMessages'
import { notifySuccess } from '../../../components/notify'
import type { useDeleteTask } from '../hooks/useTaskMutations'
import type { Task } from '../hooks/useTasks'

interface ConfirmDeleteModalProps {
  task: Task
  opened: boolean
  onClose: () => void
  /** The task's delete mutation, owned by TaskActions so the task's other actions wait too. */
  remove: ReturnType<typeof useDeleteTask>
}

/** Delete asks first (spec section 8): the API keeps no archive. */
export function ConfirmDeleteModal({ task, opened, onClose, remove }: ConfirmDeleteModalProps) {
  const [failure, setFailure] = useState<ErrorDescription | null>(null)
  const deleting = remove.isPending
  const close = () => {
    if (deleting) return
    setFailure(null)
    onClose()
  }

  async function confirm() {
    setFailure(null)
    try {
      await remove.mutateAsync()
      notifySuccess('Task deleted.')
      onClose()
    } catch (error) {
      setFailure(describeError(error))
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={close}
      title="Delete task"
      closeOnClickOutside={!deleting}
      closeOnEscape={!deleting}
      withCloseButton={!deleting}
      closeButtonProps={{ 'aria-label': 'Close' }}
    >
      <Stack>
        {failure && (
          <Alert color="red" variant="light" title={failure.title}>
            {failure.message}
          </Alert>
        )}
        <Text style={{ overflowWrap: 'anywhere' }}>
          Delete “{task.title}”? There&apos;s no undo: the task is gone for good.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={close} disabled={deleting} data-autofocus>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleting}
            onClick={() => {
              void confirm()
            }}
          >
            Delete
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
