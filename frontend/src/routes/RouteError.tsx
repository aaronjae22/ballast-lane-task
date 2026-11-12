import type { ReactElement } from 'react'

/** Shown by the router when a route throws while rendering. */
export function RouteError(): ReactElement {
  throw new Error('not implemented')
}
