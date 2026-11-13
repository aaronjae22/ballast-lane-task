import { Alert, Anchor, Paper, Stack, Text, Title } from '@mantine/core'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError } from '../../api/errors'
import { notifySuccess } from '../../components/notify'
import { QueryErrorAlert } from '../../components/QueryErrorAlert'
import { TaskForm } from '../../features/tasks/components/TaskForm'
import { positiveInteger } from '../../features/tasks/filters'
import { useListState } from '../../features/tasks/listLink'
import { useUpdateTask } from '../../features/tasks/hooks/useTaskMutations'
import { useTask, type Task } from '../../features/tasks/hooks/useTasks'
import { can } from '../../features/tasks/permissions'
import { toUpdateRequest, type TaskFormValues } from '../../features/tasks/schemas'
import { useCurrentUser } from '../../features/users/hooks/useCurrentUser'
import { TaskLoading, TaskNotFound } from './TaskPageStates'

export function EditTaskPage() {
  const { taskId = '' } = useParams()
  const id = positiveInteger(taskId)
  return id === null ? <TaskNotFound /> : <EditTask id={id} />
}

function EditTask({ id }: { id: number }) {
  const task = useTask(id)
  const me = useCurrentUser()
  const update = useUpdateTask(id)
  const navigate = useNavigate()
  const fromList = useListState()
  const taskPath = `/tasks/${String(id)}`

  if (task.isPending || me.isPending) return <TaskLoading />
  if (task.isError && task.error instanceof ApiError && task.error.status === 404) {
    return <TaskNotFound />
  }
  if (task.isError || me.isError) {
    const failed = task.isError ? task : me
    return (
      <QueryErrorAlert
        error={failed.error}
        onRetry={() => {
          void failed.refetch()
        }}
      />
    )
  }

  return (
    <Stack gap="md" maw={640}>
      <Anchor component={Link} to={taskPath} state={fromList} size="sm">
        Back to the task
      </Anchor>
      <Title order={1}>Edit task</Title>
      {/* The API would answer 403; the page says so before anything is typed. */}
      {can(me.data, task.data, 'edit') ? (
        <Paper withBorder radius="md" p="md">
          <TaskForm
            submitLabel="Save changes"
            cancelTo={taskPath}
            cancelState={fromList}
            defaultValues={formValuesOf(task.data)}
            withAssignee={false}
            onSubmit={async (values, changed) => {
              const body = toUpdateRequest(values, changed)
              if (Object.keys(body).length > 0) {
                await update.mutateAsync(body)
                notifySuccess('Changes saved.')
              }
              await navigate(taskPath, { state: fromList })
            }}
          />
        </Paper>
      ) : (
        <Alert color="yellow" variant="light" title="Not allowed">
          <Text size="sm">Only the task&apos;s owner or an admin can edit it.</Text>
        </Alert>
      )}
    </Stack>
  )
}

function formValuesOf(task: Task): TaskFormValues {
  return {
    title: task.title,
    description: task.description,
    due_date: task.due_date,
    assignee_id: task.assignee?.id ?? null,
  }
}
