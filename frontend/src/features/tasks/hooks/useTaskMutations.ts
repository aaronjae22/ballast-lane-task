import {
  useMutation,
  useQueryClient,
  type QueryClient,
  type UseMutationResult,
} from '@tanstack/react-query'
import { ApiError, unwrap } from '../../../api/errors'
import { useApi } from '../../../auth/useAuth'
import type { Transition } from '../permissions'
import type { TaskCreateRequest, TaskUpdateRequest } from '../schemas'
import { taskKeys } from './keys'
import type { Task } from './useTasks'

// Mutations are never retried (ADR 0018): a request that got no answer may have been applied,
// and a retry could create a task twice. TanStack Query's default for mutations is no retry.

/** POST /api/tasks/. On success every list is marked stale, so each shows the new task. */
export function useCreateTask(): UseMutationResult<Task, Error, TaskCreateRequest> {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body) => unwrap<Task>(await api.POST('/api/tasks/', { body })),
    onSuccess: () => {
      // Not awaited: the user moves on while any list on screen refetches.
      void queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/** PATCH /api/tasks/{id}/ with the changed fields. */
export function useUpdateTask(id: number): UseMutationResult<Task, Error, TaskUpdateRequest> {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body) =>
      unwrap<Task>(await api.PATCH('/api/tasks/{id}/', { params: { path: { id } }, body })),
    onSuccess: (task) => {
      storeTask(queryClient, task)
    },
    onError: (error) => {
      refreshAfterError(queryClient, id, error)
    },
  })
}

/** POST /api/tasks/{id}/start/, /complete/ or /reopen/, which take no body. */
export function useTaskTransition(id: number): UseMutationResult<Task, Error, Transition> {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (transition) => {
      const options = { params: { path: { id } } }
      const result =
        transition === 'start'
          ? await api.POST('/api/tasks/{id}/start/', options)
          : transition === 'complete'
            ? await api.POST('/api/tasks/{id}/complete/', options)
            : await api.POST('/api/tasks/{id}/reopen/', options)
      return unwrap<Task>(result)
    },
    onSuccess: (task) => {
      storeTask(queryClient, task)
    },
    onError: (error) => {
      refreshAfterError(queryClient, id, error)
    },
  })
}

/** POST /api/tasks/{id}/assign/ with an active user's id, or null to unassign. */
export function useAssignTask(id: number): UseMutationResult<Task, Error, number | null> {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (assigneeId) =>
      unwrap<Task>(
        await api.POST('/api/tasks/{id}/assign/', {
          params: { path: { id } },
          body: { assignee_id: assigneeId },
        }),
      ),
    onSuccess: (task) => {
      storeTask(queryClient, task)
    },
    onError: (error) => {
      refreshAfterError(queryClient, id, error)
    },
  })
}

// After a change (ADR 0018): the returned task replaces the cached one, but only if it is still
// cached. After a logout the cache is empty (ADR 0016), and a late answer mustn't refill it.
// Every list is marked stale, since the change can move the task in or out of one.
function storeTask(queryClient: QueryClient, task: Task): void {
  const key = taskKeys.detail(task.id)
  if (queryClient.getQueryData(key) !== undefined) queryClient.setQueryData(key, task)
  void queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
}

// A 404: the task is gone, or no longer visible. A 403 or 409: it changed elsewhere, and the
// screens should catch up with it (ADR 0018).
function refreshAfterError(queryClient: QueryClient, id: number, error: Error): void {
  if (!(error instanceof ApiError)) return
  if (error.status === 404) {
    queryClient.removeQueries({ queryKey: taskKeys.detail(id) })
  } else if (error.status === 403 || error.status === 409) {
    void queryClient.invalidateQueries({ queryKey: taskKeys.detail(id) })
  } else {
    return
  }
  void queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
}
