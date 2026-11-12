import { Button, Group, Paper, Skeleton, Stack, Text, Title } from '@mantine/core'
import { Link } from 'react-router'
import { QueryErrorAlert } from '../../components/QueryErrorAlert'
import { TaskList } from '../../features/tasks/components/TaskList'
import { noFilters, toSearchParams } from '../../features/tasks/filters'
import { useTaskFilters } from '../../features/tasks/hooks/useTaskFilters'
import { useTasks } from '../../features/tasks/hooks/useTasks'

export function TaskListPage() {
  const { filters, setFilters } = useTaskFilters()
  const tasks = useTasks(filters)
  const filtered = toSearchParams({ ...filters, page: 1 }).toString() !== ''

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={1}>Tasks</Title>
        <Button component={Link} to="/tasks/new">
          New task
        </Button>
      </Group>

      {tasks.isPending ? (
        <Stack role="status" aria-label="Loading tasks" gap="sm">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} height={72} radius="md" />
          ))}
        </Stack>
      ) : tasks.isError ? (
        <QueryErrorAlert
          error={tasks.error}
          onRetry={() => {
            void tasks.refetch()
          }}
        />
      ) : tasks.data.results.length === 0 ? (
        filtered ? (
          <EmptyState
            title="No tasks match these filters"
            message="Try other filters, or clear them to see every task."
            action={
              <Button
                variant="light"
                onClick={() => {
                  setFilters(noFilters)
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="No tasks yet"
            message="Create a task, or ask a teammate to assign you one."
            action={
              <Button component={Link} to="/tasks/new" variant="light">
                Create a task
              </Button>
            }
          />
        )
      ) : (
        <>
          <Text size="sm" c="dimmed">
            {tasks.data.count === 1 ? '1 task' : `${String(tasks.data.count)} tasks`}
          </Text>
          <TaskList tasks={tasks.data.results} />
        </>
      )}
    </Stack>
  )
}

function EmptyState({
  title,
  message,
  action,
}: {
  title: string
  message: string
  action: React.ReactNode
}) {
  return (
    <Paper withBorder radius="md" p="xl">
      <Stack align="center" gap="xs" ta="center">
        <Text fw={600}>{title}</Text>
        <Text size="sm" c="dimmed">
          {message}
        </Text>
        {action}
      </Stack>
    </Paper>
  )
}
