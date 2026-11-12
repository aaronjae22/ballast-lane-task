import { Anchor, Group, Table, Text } from '@mantine/core'
import { Link } from 'react-router'
import { formatDay } from '../dates'
import type { Task } from '../hooks/useTasks'
import { OverdueBadge, TaskStatusBadge } from './TaskStatusBadge'

/** The list from the `sm` breakpoint up: a column for each detail. */
export function TaskTable({ tasks }: { tasks: Task[] }) {
  return (
    <Table aria-label="Tasks" highlightOnHover verticalSpacing="sm">
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Title</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Due date</Table.Th>
          <Table.Th>Owner</Table.Th>
          <Table.Th>Assignee</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {tasks.map((task) => (
          <Table.Tr key={task.id}>
            <Table.Td>
              <Anchor component={Link} to={`/tasks/${String(task.id)}`} fw={600}>
                {task.title}
              </Anchor>
            </Table.Td>
            <Table.Td>
              <TaskStatusBadge status={task.status} />
            </Table.Td>
            <Table.Td>
              <Group gap="xs" wrap="nowrap">
                <Text size="sm" c={task.due_date === null ? 'dimmed' : undefined}>
                  {task.due_date === null ? 'No due date' : formatDay(task.due_date)}
                </Text>
                {task.is_overdue && <OverdueBadge />}
              </Group>
            </Table.Td>
            <Table.Td>{task.owner.name}</Table.Td>
            <Table.Td>
              {task.assignee?.name ?? (
                <Text size="sm" c="dimmed">
                  Unassigned
                </Text>
              )}
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}
