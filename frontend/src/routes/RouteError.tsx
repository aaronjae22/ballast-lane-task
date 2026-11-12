import type { ReactElement } from 'react'
import { FullPageError } from '../components/FullPageError'

/** Shown by the router when a route throws while rendering. */
export function RouteError(): ReactElement {
  return (
    <FullPageError
      title="Something went wrong"
      message="This page hit an unexpected error. Reloading it usually helps."
      actionLabel="Reload the page"
      onAction={() => {
        window.location.reload()
      }}
    />
  )
}
