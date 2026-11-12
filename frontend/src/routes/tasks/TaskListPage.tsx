import { Alert, Button, Group, Paper, Skeleton, Stack, Text, Title } from '@mantine/core'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../../api/errors'
import { QueryErrorAlert } from '../../components/QueryErrorAlert'
import { TaskFilters } from '../../features/tasks/components/TaskFilters'
import { TaskList } from '../../features/tasks/components/TaskList'
import { TaskPagination } from '../../features/tasks/components/TaskPagination'
import {
  noFilters,
  toSearchParams,
  type TaskFilters as Filters,
} from '../../features/tasks/filters'
import { useTaskFilters } from '../../features/tasks/hooks/useTaskFilters'
import { useTasks } from '../../features/tasks/hooks/useTasks'

const filterNames: Record<keyof Filters, string> = {
  status: 'Status',
  due_after: 'Due from',
  due_before: 'Due until',
  overdue: 'Overdue',
  assignee: 'Assignee',
  search: 'Search',
  ordering: 'Order',
  page: 'Page',
}

export function TaskListPage() {
  const { filters, ignored, setFilters } = useTaskFilters()
  const tasks = useTasks(filters)
  const filtered = toSearchParams({ ...filters, page: 1 }).toString() !== ''
  // The API answers a page past the end with 404 (ADR 0014), for example after the last task
  // on the last page was deleted. That's an empty page, not a missing task.
  const pastTheEnd =
    tasks.error instanceof ApiError && tasks.error.status === 404 && filters.page > 1

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={1}>Tasks</Title>
        <Button component={Link} to="/tasks/new">
          New task
        </Button>
      </Group>

      {ignored.length > 0 && (
        <Alert color="yellow" variant="light" title="Some filters in this link weren't valid">
          These were ignored: {ignored.map((name) => filterNames[name]).join(', ')}.
        </Alert>
      )}

      <TaskFilters filters={filters} setFilters={setFilters} />

      {tasks.isPending ? (
        <Stack role="status" aria-label="Loading tasks" gap="sm">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} height={72} radius="md" />
          ))}
        </Stack>
      ) : pastTheEnd ? (
        <EmptyState
          title={`No tasks on page ${String(filters.page)}`}
          message="This page is past the end of the list."
          action={
            <Button
              variant="light"
              onClick={() => {
                setFilters({ page: 1 })
              }}
            >
              Go to page 1
            </Button>
          }
        />
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
          <TaskPagination
            count={tasks.data.count}
            page={filters.page}
            onChange={(page) => {
              setFilters({ page })
            }}
          />
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
  action: ReactNode
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
