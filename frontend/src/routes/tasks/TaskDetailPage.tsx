import { Anchor, Button, Group, Paper, Stack, Title } from '@mantine/core'
import { Link, useParams } from 'react-router'
import { ApiError } from '../../api/errors'
import { QueryErrorAlert } from '../../components/QueryErrorAlert'
import { TaskActions } from '../../features/tasks/components/TaskActions'
import { TaskDetails } from '../../features/tasks/components/TaskDetails'
import { positiveInteger } from '../../features/tasks/filters'
import { useTask } from '../../features/tasks/hooks/useTasks'
import { can } from '../../features/tasks/permissions'
import { useCurrentUser } from '../../features/users/hooks/useCurrentUser'
import { TaskLoading, TaskNotFound } from './TaskPageStates'

export function TaskDetailPage() {
  const { taskId = '' } = useParams()
  const id = positiveInteger(taskId)
  // /tasks/abc can't be a task, so there's nothing to ask the API.
  return id === null ? <TaskNotFound /> : <TaskView id={id} />
}

function TaskView({ id }: { id: number }) {
  const task = useTask(id)
  const me = useCurrentUser()

  if (task.isPending) return <TaskLoading />
  if (task.isError) {
    if (task.error instanceof ApiError && task.error.status === 404) return <TaskNotFound />
    return (
      <Stack gap="md">
        <BackToTasks />
        <QueryErrorAlert
          error={task.error}
          onRetry={() => {
            void task.refetch()
          }}
        />
      </Stack>
    )
  }
  return (
    <Stack gap="md">
      <BackToTasks />
      <Title order={1} style={{ overflowWrap: 'anywhere' }}>
        {task.data.title}
      </Title>
      <Group gap="xs">
        <TaskActions task={task.data} />
        {can(me.data, task.data, 'edit') && (
          <Button component={Link} to={`/tasks/${String(id)}/edit`} variant="default" size="xs">
            Edit
          </Button>
        )}
      </Group>
      <Paper withBorder radius="md" p="md">
        <TaskDetails task={task.data} />
      </Paper>
    </Stack>
  )
}

function BackToTasks() {
  return (
    <Anchor component={Link} to="/tasks" size="sm">
      Back to tasks
    </Anchor>
  )
}
