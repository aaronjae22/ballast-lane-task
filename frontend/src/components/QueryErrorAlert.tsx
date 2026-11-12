import type { ReactElement } from 'react'

export interface QueryErrorAlertProps {
  error: unknown
  /** Shown as a "Try again" button when the error is one that asking again can fix. */
  onRetry?: () => void
}

/** The error state of anything loaded from the API: what went wrong, and a retry. */
export function QueryErrorAlert(_props: QueryErrorAlertProps): ReactElement | null {
  return null
}
