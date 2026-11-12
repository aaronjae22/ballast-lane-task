/** A response the API answered with an error status. */
export class ApiError extends Error {
  override readonly name = 'ApiError'
  readonly status: number
  /** The parsed error body: {"detail": "..."}, or field errors for a 400 (ADR 0014). */
  readonly body: unknown
  /** Seconds from the Retry-After header (sent with 429), or null without one. */
  readonly retryAfter: number | null

  constructor(response: Response, body: unknown) {
    super(detailOf(body) ?? `The API answered ${String(response.status)}.`)
    this.status = response.status
    this.body = body
    this.retryAfter = secondsOf(response.headers.get('Retry-After'))
  }
}

type FetchResult<T> =
  | { data: T; error?: never; response: Response }
  | { data?: never; error: unknown; response: Response }

/** The data of a successful openapi-fetch result; throws ApiError for an error status. */
export function unwrap<T>(result: FetchResult<T>): T {
  if (!result.response.ok) throw new ApiError(result.response, result.error)
  return result.data as T
}

function detailOf(body: unknown): string | null {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    return typeof body.detail === 'string' ? body.detail : null
  }
  return null
}

// DRF sends Retry-After as whole seconds. The HTTP-date form isn't used by the API.
function secondsOf(header: string | null): number | null {
  if (header === null || header.trim() === '') return null
  const seconds = Number(header)
  return Number.isInteger(seconds) && seconds >= 0 ? seconds : null
}
