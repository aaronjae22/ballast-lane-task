import type { components, paths } from '../api/generated/schema'

/** The API's schemas, for typing MSW response bodies: a field the API dropped fails tsc. */
export type Schemas = components['schemas']

/**
 * The absolute URL of an API path, for MSW handlers. The path is typed against the generated
 * schema, so a renamed endpoint fails type checking. `{id}` becomes MSW's `:id`.
 */
export function apiUrl(path: keyof paths): string {
  return new URL(path.replace(/\{(\w+)\}/g, ':$1'), window.location.origin).href
}
