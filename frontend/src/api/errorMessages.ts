import { ApiError } from './errors'

// The one place an error becomes words for the user (ADR 0018). Screens show what this returns
// and decide only where: on form fields, in an alert, or in a notification.

/** What kind of failure an error is, which decides what the user is told (ADR 0018). */
export type ErrorKind =
  | 'invalid'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'throttled'
  | 'unavailable'
  | 'unexpected'

export interface ErrorDescription {
  kind: ErrorKind
  title: string
  message: string
}

/** Field errors keyed by field. */
export type FieldErrors = Record<string, string[]>

const unavailable: ErrorDescription = {
  kind: 'unavailable',
  title: "Can't reach the server",
  message: 'Check your connection, then try again.',
}

/**
 * A 404, and also a task id that can't exist. Deleted and not visible are the same answer
 * (ADR 0003), and so is the message.
 */
export const taskNotFound: ErrorDescription = {
  kind: 'not_found',
  title: 'Task not found',
  message: "It may have been deleted, or it's no longer shared with you.",
}

// A 405 or 415 means the app sent something the API never takes: a bug, not the user's doing.
const unexpected: ErrorDescription = {
  kind: 'unexpected',
  title: 'Something went wrong',
  message: 'Reload the page and try again.',
}

/** What to tell the user about any error a request can end with. */
export function describeError(error: unknown): ErrorDescription {
  // fetch rejects with a TypeError when no response came back at all.
  if (error instanceof TypeError) return unavailable
  if (!(error instanceof ApiError)) return unexpected

  const detail = detailOf(error.body)
  switch (error.status) {
    case 400: {
      const messages = [...new Set(Object.values(fieldErrorsOf(error) ?? {}).flat())]
      return {
        kind: 'invalid',
        title: "Some values weren't accepted",
        message: messages.length > 0 ? messages.join(' ') : 'Check the values and try again.',
      }
    }
    case 401:
      // The fetch wrapper has already refreshed and retried once (ADR 0016).
      return {
        kind: 'unauthorized',
        title: 'Your session has ended',
        message: 'Log in again to continue.',
      }
    case 403:
      return {
        kind: 'forbidden',
        title: 'Not allowed',
        message: detail ?? "You don't have permission to do that.",
      }
    case 404:
      return taskNotFound
    case 409:
      return {
        kind: 'conflict',
        title: "The task's status changed",
        message: detail ?? 'Someone else changed this task. Its latest state is shown.',
      }
    case 429:
      return {
        kind: 'throttled',
        title: 'Too many requests',
        message: `Try again in ${error.retryAfter === null ? 'a minute' : seconds(error.retryAfter)}.`,
      }
  }
  return error.status >= 500 ? unavailable : unexpected
}

/** A 400's messages by field (ADR 0014), or null for any other error. */
export function fieldErrorsOf(error: unknown): FieldErrors | null {
  if (!(error instanceof ApiError) || error.status !== 400) return null
  const { body } = error
  if (typeof body !== 'object' || body === null || Array.isArray(body)) return null
  const entries = Object.entries(body)
  const isFieldErrors = entries.every(
    ([, messages]) => Array.isArray(messages) && messages.every((m) => typeof m === 'string'),
  )
  return isFieldErrors ? Object.fromEntries<string[]>(entries) : null
}

function detailOf(body: unknown): string | null {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    return typeof body.detail === 'string' && body.detail !== '' ? body.detail : null
  }
  return null
}

function seconds(count: number): string {
  return count === 1 ? '1 second' : `${String(count)} seconds`
}
