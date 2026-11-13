import { Button, Group, Menu } from '@mantine/core'
import { useState } from 'react'
import { Link } from 'react-router'
import { notifyError, notifySuccess } from '../../../components/notify'
import { useCurrentUser } from '../../users/hooks/useCurrentUser'
import { useAssignTask, useTaskTransition } from '../hooks/useTaskMutations'
import type { Task } from '../hooks/useTasks'
import { can, transitionsFrom, type Transition } from '../permissions'
import { AssignModal } from './AssignModal'

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
 * What the user may do to the task, for the list's rows and the task page (ADR 0018): the
 * status changes as buttons, then a More menu with Assign and Edit. While a change runs, its
 * button spins and the task's other actions are disabled.
 */
export function TaskActions({ task }: { task: Task }) {
  const me = useCurrentUser()
  const transition = useTaskTransition(task.id)
  const assign = useAssignTask(task.id)
  const [assigning, setAssigning] = useState(false)
  const busy = transition.isPending || assign.isPending
  const canChangeStatus = can(me.data, task, 'change_status')
  const canAssign = can(me.data, task, 'assign')
  const canEdit = can(me.data, task, 'edit')

  if (!canChangeStatus && !canAssign && !canEdit) return null

  return (
    <Group gap="xs">
      {(canChangeStatus ? transitionsFrom(task.status) : []).map((name) => (
        <Button
          key={name}
          size="xs"
          variant={name === 'complete' ? 'filled' : 'light'}
          loading={transition.isPending && transition.variables === name}
          disabled={busy && !(transition.isPending && transition.variables === name)}
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
      {(canAssign || canEdit) && (
        <Menu position="bottom-end">
          <Menu.Target>
            <Button size="xs" variant="default" disabled={busy}>
              More
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            {canAssign && (
              <Menu.Item
                onClick={() => {
                  setAssigning(true)
                }}
              >
                Assign…
              </Menu.Item>
            )}
            {canEdit && (
              <Menu.Item component={Link} to={`/tasks/${String(task.id)}/edit`}>
                Edit
              </Menu.Item>
            )}
          </Menu.Dropdown>
        </Menu>
      )}
      {canAssign && (
        <AssignModal
          task={task}
          opened={assigning}
          onClose={() => {
            setAssigning(false)
          }}
          assign={assign}
        />
      )}
    </Group>
  )
}
