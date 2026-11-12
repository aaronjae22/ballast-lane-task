import { MantineProvider } from '@mantine/core'
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

/** Mantine, then TanStack Query, then the session, then the routes, which use all three. */
export function AppProviders({
  auth,
  queryClient,
  router,
  mantineEnv = 'default',
}: AppProvidersProps): ReactElement {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light" env={mantineEnv}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider auth={auth}>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>
  )
}
