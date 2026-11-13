import { Button, Skeleton, Stack } from '@mantine/core'
import { Link } from 'react-router'
import { taskNotFound } from '../../api/errorMessages'
import { EmptyState } from '../../components/EmptyState'

// The states every page about one task shares: the task page and its edit page.

export function TaskLoading() {
  return (
    <Stack role="status" aria-label="Loading the task" gap="sm">
      <Skeleton height={36} width="60%" />
      <Skeleton height={160} radius="md" />
    </Stack>
  )
}

/** A 404, or an id that can't be a task. */
export function TaskNotFound() {
  return (
    <EmptyState
      title={taskNotFound.title}
      message={taskNotFound.message}
      action={
        <Button component={Link} to="/tasks" variant="light">
          Back to tasks
        </Button>
      }
    />
  )
}
