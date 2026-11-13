import { Paper, Stack, Title } from '@mantine/core'
import { useNavigate } from 'react-router'
import { notifySuccess } from '../../components/notify'
import { TaskForm } from '../../features/tasks/components/TaskForm'
import { useCreateTask } from '../../features/tasks/hooks/useTaskMutations'
import { toCreateRequest } from '../../features/tasks/schemas'

export function CreateTaskPage() {
  const create = useCreateTask()
  const navigate = useNavigate()

  return (
    <Stack maw={640}>
      <Title order={1}>New task</Title>
      <Paper withBorder p="md">
        <TaskForm
          submitLabel="Create task"
          cancelTo="/tasks"
          onSubmit={async (values) => {
            const task = await create.mutateAsync(toCreateRequest(values))
            notifySuccess('Task created.')
            await navigate(`/tasks/${String(task.id)}`)
          }}
        />
      </Paper>
    </Stack>
  )
}
