import { useMantineTheme } from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import type { Task } from '../hooks/useTasks'
import { TaskCards } from './TaskCards'
import { TaskTable } from './TaskTable'

/**
 * A table from the `sm` breakpoint up, cards below it (ADR 0018). Only one of the two is
 * rendered, and the media query is read on the first render, so neither flashes.
 */
export function TaskList({ tasks }: { tasks: Task[] }) {
  const theme = useMantineTheme()
  const wide = useMediaQuery(`(min-width: ${theme.breakpoints.sm})`, false, {
    getInitialValueInEffect: false,
  })
  return wide ? <TaskTable tasks={tasks} /> : <TaskCards tasks={tasks} />
}
