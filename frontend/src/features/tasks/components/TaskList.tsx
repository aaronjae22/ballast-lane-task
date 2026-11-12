import type { Task } from '../hooks/useTasks'
import { useWideScreen } from '../hooks/useWideScreen'
import { TaskCards } from './TaskCards'
import { TaskTable } from './TaskTable'

/** A table from the `sm` breakpoint up, cards below it (ADR 0018). Only one is rendered. */
export function TaskList({ tasks }: { tasks: Task[] }) {
  return useWideScreen() ? <TaskTable tasks={tasks} /> : <TaskCards tasks={tasks} />
}
