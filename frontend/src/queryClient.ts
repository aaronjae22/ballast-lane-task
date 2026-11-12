import type { QueryClient } from '@tanstack/react-query'

/** The app's query client. Client errors (4xx) aren't retried: asking again won't help. */
export function createQueryClient(): QueryClient {
  throw new Error('not implemented')
}
