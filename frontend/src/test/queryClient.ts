import { QueryClient } from '@tanstack/react-query'

/** A query client for tests: no retries, so an error shows at once. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}
