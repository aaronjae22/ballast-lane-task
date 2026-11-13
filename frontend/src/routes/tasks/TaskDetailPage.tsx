import { Anchor, Paper, Stack, Title } from '@mantine/core'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { ApiError } from '../../api/errors'
import { QueryErrorAlert } from '../../components/QueryErrorAlert'
import { TaskActions } from '../../features/tasks/components/TaskActions'
import { TaskDetails } from '../../features/tasks/components/TaskDetails'
import { positiveInteger } from '../../features/tasks/filters'
import { listPathFrom } from '../../features/tasks/listLink'
import { useTask } from '../../features/tasks/hooks/useTasks'
import { TaskLoading, TaskNotFound } from './TaskPageStates'

export function TaskDetailPage() {
  const { taskId = '' } = useParams()
  const id = positiveInteger(taskId)
  // /tasks/abc can't be a task, so there's nothing to ask the API.
  return id === null ? <TaskNotFound /> : <TaskView id={id} />
}

function TaskView({ id }: { id: number }) {
  const task = useTask(id)
  const navigate = useNavigate()
  // The list this task was opened from, with its filters (listLink.ts).
  const listPath = listPathFrom(useLocation().state)

  if (task.isPending) return <TaskLoading />
  if (task.isError) {
    if (task.error instanceof ApiError && task.error.status === 404) return <TaskNotFound />
    return (
      <Stack gap="md">
        <BackToTasks to={listPath} />
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
      <BackToTasks to={listPath} />
      <Title order={1} style={{ overflowWrap: 'anywhere' }}>
        {task.data.title}
      </Title>
      <TaskActions task={task.data} onDeleted={() => navigate(listPath)} />
      <Paper withBorder radius="md" p="md">
        <TaskDetails task={task.data} />
      </Paper>
    </Stack>
  )
}

function BackToTasks({ to }: { to: string }) {
  return (
    <Anchor component={Link} to={to} size="sm">
      Back to tasks
    </Anchor>
  )
}
