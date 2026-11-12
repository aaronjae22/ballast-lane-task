import type { Client } from 'openapi-fetch'
import type { paths } from './generated/schema'

/** The typed client for the whole API, generated from its OpenAPI schema. */
export type ApiClient = Client<paths>

export interface ApiClientOptions {
  /** Sends each request. Defaults to the global fetch, looked up when the request is sent. */
  fetch?: (request: Request) => Promise<Response>
  /** Defaults to the page's own origin: the API is always same-origin (ADR 0006). */
  baseUrl?: string
}

export function createApiClient(_options: ApiClientOptions = {}): ApiClient {
  throw new Error('not implemented')
}
