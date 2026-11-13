import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import type { ComponentProps, ReactElement } from 'react'
import { RouterProvider } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import type { Auth } from './auth/createAuth'
import { theme } from './theme'

export interface AppProvidersProps {
  auth: Auth
  queryClient: QueryClient
  router: ComponentProps<typeof RouterProvider>['router']
  /** Mantine's test mode turns off transitions; tests pass 'test'. */
  mantineEnv?: 'default' | 'test'
}

/** Mantine and its notifications, then TanStack Query, then the session, then the routes. */
export function AppProviders({
  auth,
  queryClient,
  router,
  mantineEnv = 'default',
}: AppProvidersProps): ReactElement {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light" env={mantineEnv}>
      {/* Where the results of actions are reported, on every page (ADR 0018). */}
      <Notifications />
      <QueryClientProvider client={queryClient}>
        <AuthProvider auth={auth}>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>
  )
}
