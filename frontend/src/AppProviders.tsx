import type { QueryClient } from '@tanstack/react-query'
import type { ComponentProps, ReactElement } from 'react'
import type { RouterProvider } from 'react-router'
import type { Auth } from './auth/createAuth'

export interface AppProvidersProps {
  auth: Auth
  queryClient: QueryClient
  router: ComponentProps<typeof RouterProvider>['router']
  /** Mantine's test mode turns off transitions; tests pass 'test'. */
  mantineEnv?: 'default' | 'test'
}

/** Mantine, then TanStack Query, then the session, then the routes, which use all three. */
export function AppProviders(_props: AppProvidersProps): ReactElement {
  throw new Error('not implemented')
}
