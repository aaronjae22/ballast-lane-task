import { Button, Group } from '@mantine/core'
import { notifyError, notifySuccess } from '../../../components/notify'
import { useCurrentUser } from '../../users/hooks/useCurrentUser'
import { useTaskTransition } from '../hooks/useTaskMutations'
import type { Task } from '../hooks/useTasks'
import { can, transitionsFrom, type Transition } from '../permissions'

const labels: Record<Transition, string> = {
  start: 'Start',
  complete: 'Complete',
  reopen: 'Reopen',
}

const results: Record<Transition, string> = {
  start: 'Task started.',
  complete: 'Task completed.',
  reopen: 'Task reopened.',
}

/**
 * The status changes the user may make to the task, for the list's rows and the task page
 * (ADR 0018). While one runs, its button spins and the others are disabled.
 */
export function TaskActions({ task }: { task: Task }) {
  const me = useCurrentUser()
  const transition = useTaskTransition(task.id)

  if (!can(me.data, task, 'change_status')) return null

  return (
    <Group gap="xs">
      {transitionsFrom(task.status).map((name) => (
        <Button
          key={name}
          size="xs"
          variant={name === 'complete' ? 'filled' : 'light'}
          loading={transition.isPending && transition.variables === name}
          disabled={transition.isPending && transition.variables !== name}
          onClick={() => {
            // The promise settles even if the row has gone from a filtered list by then.
            transition.mutateAsync(name).then(() => {
              notifySuccess(results[name])
            }, notifyError)
          }}
        >
          {labels[name]}
        </Button>
      ))}
    </Group>
  )
}
