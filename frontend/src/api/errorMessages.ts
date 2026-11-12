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

/** What to tell the user about any error a request can end with. */
export function describeError(_error: unknown): ErrorDescription {
  throw new Error('not implemented')
}

/** A 400's messages by field (ADR 0014), or null for any other error. */
export function fieldErrorsOf(_error: unknown): FieldErrors | null {
  throw new Error('not implemented')
}
