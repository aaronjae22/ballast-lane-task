import { MantineProvider } from '@mantine/core'
import { type QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { StrictMode, type ReactElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { AppProviders } from '../AppProviders'
import { createAuth, type Auth } from '../auth/createAuth'
import { createRoutes } from '../routes/router'
import { theme } from '../theme'
import { createTestQueryClient } from './queryClient'

/** Renders the whole app at `path`, under StrictMode as in development (ADR 0016). */
export function renderApp({
  path = '/',
  auth = createAuth(),
  queryClient = createTestQueryClient(),
}: { path?: string; auth?: Auth; queryClient?: QueryClient } = {}) {
  const router = createMemoryRouter(createRoutes(), { initialEntries: [path] })
  render(
    <StrictMode>
      <AppProviders auth={auth} queryClient={queryClient} router={router} mantineEnv="test" />
    </StrictMode>,
  )
  return { auth, queryClient, router }
}

/** Renders one component inside Mantine, under StrictMode, for tests that need no routes. */
export function renderUi(ui: ReactElement) {
  return render(
    <StrictMode>
      <MantineProvider theme={theme} env="test">
        {ui}
      </MantineProvider>
    </StrictMode>,
  )
}
