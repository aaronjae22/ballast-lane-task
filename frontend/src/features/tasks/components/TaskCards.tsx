import { Anchor, Group, Paper, Stack, Text } from '@mantine/core'
import { Link } from 'react-router'
import { formatDay } from '../dates'
import type { Task } from '../hooks/useTasks'
import { TaskActions } from './TaskActions'
import { OverdueBadge, TaskStatusBadge } from './TaskStatusBadge'

/** The list below the `sm` breakpoint: one card per task, which fits in 360 px. */
export function TaskCards({ tasks }: { tasks: Task[] }) {
  return (
    // role="list" because Safari drops a list's semantics once its bullets are hidden.
    <Stack
      component="ul"
      role="list"
      aria-label="Tasks"
      gap="sm"
      m={0}
      p={0}
      style={{ listStyle: 'none' }}
    >
      {tasks.map((task) => (
        <Paper component="li" key={task.id} withBorder radius="md" p="sm">
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
            <Anchor component={Link} to={`/tasks/${String(task.id)}`} fw={600} miw={0}>
              {task.title}
            </Anchor>
            <TaskStatusBadge status={task.status} />
          </Group>
          <Group gap="xs" mt={4}>
            <Text size="sm" c="dimmed">
              {task.due_date === null ? 'No due date' : `Due ${formatDay(task.due_date)}`}
            </Text>
            {task.is_overdue && <OverdueBadge />}
          </Group>
          <Text size="sm" c="dimmed">
            Owner: {task.owner.name} · Assignee: {task.assignee?.name ?? 'Unassigned'}
          </Text>
          <Group mt="xs">
            <TaskActions task={task} />
          </Group>
        </Paper>
      ))}
    </Stack>
  )
}
