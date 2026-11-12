import createClient, {
  createQuerySerializer,
  serializeArrayParam,
  type Client,
} from 'openapi-fetch'
import type { paths } from './generated/schema'

/** The typed client for the whole API, generated from its OpenAPI schema. */
export type ApiClient = Client<paths>

export interface ApiClientOptions {
  /** Sends each request. Defaults to the global fetch, looked up when the request is sent. */
  fetch?: (request: Request) => Promise<Response>
  /** Defaults to the page's own origin: the API is always same-origin (ADR 0006). */
  baseUrl?: string
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  // Not `fetch: globalThis.fetch`: that captures the function once, and MSW or a test stub
  // that replaces the global afterwards would never see the request.
  const send = options.fetch ?? ((request: Request) => globalThis.fetch(request))
  return createClient<paths>({
    baseUrl: options.baseUrl ?? window.location.origin,
    fetch: send,
    querySerializer: serializeQuery,
  })
}

// Array query parameters the schema declares with `explode: false`, sent as one
// comma-separated value (?ordering=status,-due_date). openapi-fetch takes serialization only
// from its options, never from the schema, and repeats every array by default. That suits
// `status` (?status=to_do&status=done), but the backend's OrderingFilter would keep only the
// last ordering. Today `ordering` is the only such parameter; one added to the schema with
// `explode: false` must be listed here too.
const commaSeparated = new Set(['ordering'])
const repeated = createQuerySerializer()

function serializeQuery(query: Record<string, unknown>): string {
  const rest: Record<string, unknown> = {}
  const joined: string[] = []
  for (const [name, value] of Object.entries(query)) {
    if (commaSeparated.has(name) && Array.isArray(value)) {
      if (value.length > 0) {
        joined.push(serializeArrayParam(name, value, { style: 'form', explode: false }))
      }
    } else {
      rest[name] = value
    }
  }
  return [repeated(rest), ...joined].filter((part) => part !== '').join('&')
}
