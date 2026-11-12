import { Badge } from '@mantine/core'
import type { Status } from '../filters'

export const statusLabels: Record<Status, string> = {
  to_do: 'To do',
  in_progress: 'In progress',
  done: 'Done',
}

const statusColors: Record<Status, string> = { to_do: 'gray', in_progress: 'blue', done: 'green' }

export function TaskStatusBadge({ status }: { status: Status }) {
  return (
    <Badge color={statusColors[status]} variant="light">
      {statusLabels[status]}
    </Badge>
  )
}

/** Shown when the API says the task is overdue: is_overdue is judged in the server's time zone. */
export function OverdueBadge() {
  return (
    <Badge color="red" variant="filled">
      Overdue
    </Badge>
  )
}
