/** A response the API answered with an error status. */
export class ApiError extends Error {
  readonly status: number
  /** The parsed error body: {"detail": "..."}, or field errors for a 400 (ADR 0014). */
  readonly body: unknown
  /** Seconds from the Retry-After header (sent with 429), or null without one. */
  readonly retryAfter: number | null

  constructor(_response: Response, _body: unknown) {
    super('not implemented')
    throw new Error('not implemented')
  }
}

type FetchResult<T> =
  | { data: T; error?: never; response: Response }
  | { data?: never; error: unknown; response: Response }

/** The data of a successful openapi-fetch result; throws ApiError for an error status. */
export function unwrap<T>(_result: FetchResult<T>): T {
  throw new Error('not implemented')
}
