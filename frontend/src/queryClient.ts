import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api/errors'

const maxRetries = 2

/** The app's query client. Client errors (4xx) aren't retried: asking again won't help. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // A 4xx answers the same every time, and retrying a 429 only adds to the throttling.
        // A 401 has already had its refresh and retry in the auth fetch wrapper.
        retry: (failures, error) =>
          !(error instanceof ApiError && error.status < 500) && failures < maxRetries,
      },
    },
  })
}
