import { Alert, Button, Stack, Text } from '@mantine/core'
import type { ReactElement } from 'react'
import { describeError, type ErrorKind } from '../api/errorMessages'

export interface QueryErrorAlertProps {
  error: unknown
  /** Shown as a "Try again" button when the error is one that asking again can fix. */
  onRetry?: () => void
}

// A 400, 403 or 404 answers the same every time (ADR 0017), and a 401 has signed the user out.
const retryable: ReadonlySet<ErrorKind> = new Set(['throttled', 'unavailable', 'unexpected'])

/** The error state of anything loaded from the API: what went wrong, and a retry. */
export function QueryErrorAlert({ error, onRetry }: QueryErrorAlertProps): ReactElement {
  const { kind, title, message } = describeError(error)
  return (
    <Alert color="red" variant="light" title={title}>
      <Stack gap="xs" align="flex-start">
        <Text size="sm">{message}</Text>
        {onRetry && retryable.has(kind) && (
          <Button size="xs" variant="light" color="red" onClick={onRetry}>
            Try again
          </Button>
        )}
      </Stack>
    </Alert>
  )
}
