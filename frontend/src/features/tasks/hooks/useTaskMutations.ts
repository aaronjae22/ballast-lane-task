import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query'
import { unwrap } from '../../../api/errors'
import { useApi } from '../../../auth/useAuth'
import type { TaskCreateRequest } from '../schemas'
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
