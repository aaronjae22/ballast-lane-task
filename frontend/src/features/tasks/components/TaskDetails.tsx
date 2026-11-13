import { Group, SimpleGrid, Stack, Text } from '@mantine/core'
import { formatDay, formatTimestamp } from '../dates'
import type { Task } from '../hooks/useTasks'
import { OverdueBadge, TaskStatusBadge } from './TaskStatusBadge'

/** Everything about one task, as the detail page shows it. */
export function TaskDetails({ task }: { task: Task }) {
  return (
    <Stack gap="md">
      <Group gap="xs">
        <TaskStatusBadge status={task.status} />
        {task.is_overdue && <OverdueBadge />}
      </Group>
      {task.description === '' ? (
        <Text c="dimmed">No description</Text>
      ) : (
        // The description is plain text: its line breaks are the author's.
        <Text style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{task.description}</Text>
      )}
      <SimpleGrid component="dl" cols={{ base: 1, xs: 2 }} spacing="md" verticalSpacing="sm" m={0}>
        <Detail label="Due date" value={task.due_date ? formatDay(task.due_date) : 'No due date'} />
        <Detail label="Owner" value={task.owner.name} />
        <Detail label="Assignee" value={task.assignee?.name ?? 'Unassigned'} />
        {task.completed_at && (
          <Detail label="Completed" value={formatTimestamp(task.completed_at)} />
        )}
        <Detail label="Created" value={formatTimestamp(task.created_at)} />
        <Detail label="Updated" value={formatTimestamp(task.updated_at)} />
      </SimpleGrid>
    </Stack>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text component="dt" size="sm" c="dimmed">
        {label}
      </Text>
      <Text component="dd" m={0}>
        {value}
      </Text>
    </div>
  )
}
