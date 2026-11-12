import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { StrictMode } from 'react'
import { createMemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AppProviders } from '../AppProviders'
import { createAuth } from '../auth/createAuth'
import { apiUrl } from '../test/api'
import { expectConsole } from '../test/console'
import { logoutSucceeds, refreshAnswers } from '../test/handlers'
import { createTestQueryClient } from '../test/queryClient'
import { renderApp } from '../test/render'
import { server } from '../test/server'
import { RouteError } from './RouteError'

const loginHeading = { name: 'Log in' }
const homeHeading = { name: 'Team Task Board' }

describe('on page load', () => {
  it('sends exactly one refresh under StrictMode', async () => {
    const refresh = refreshAnswers('access-1')
    server.use(refresh.handler)

    renderApp()

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
    expect(refresh.count()).toBe(1)
  })

  it('shows a loader, and never the login page, until the restore answers', async () => {
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.post(apiUrl('/api/auth/token/refresh/'), async () => {
        await held
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderApp()

    expect(await screen.findByRole('status', { name: 'Loading' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', loginHeading)).not.toBeInTheDocument()
    release()
    expect(await screen.findByRole('heading', loginHeading)).toBeInTheDocument()
  })

  it('shows the home page when the session is restored', async () => {
    server.use(refreshAnswers('access-1').handler)

    renderApp()

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
  })

  it('redirects to /login without a session, remembering where the user was going', async () => {
    server.use(refreshAnswers(204).handler)

    const { router } = renderApp({ path: '/' })

    expect(await screen.findByRole('heading', loginHeading)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.state).toMatchObject({ from: { pathname: '/' } })
  })

  it("shows can't-reach-the-server with a retry, which then shows the home page", async () => {
    const refresh = refreshAnswers('unreachable', 'access-1')
    server.use(refresh.handler)
    renderApp()

    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
    expect(refresh.count()).toBe(2)
  })
})

describe('later', () => {
  it('a session that becomes anonymous goes to /login with an empty query cache', async () => {
    server.use(refreshAnswers('access-1').handler, logoutSucceeds())
    const { auth, queryClient } = renderApp()
    await screen.findByRole('heading', homeHeading)
    queryClient.setQueryData(['users', 'me'], { name: 'Alice Johnson' })

    await act(() => auth.session.logout())

    expect(await screen.findByRole('heading', loginHeading)).toBeInTheDocument()
    expect(queryClient.getQueryData(['users', 'me'])).toBeUndefined()
  })
})

describe('other pages', () => {
  it('an unknown URL shows the not-found page', async () => {
    server.use(refreshAnswers(204).handler)

    renderApp({ path: '/no-such-page' })

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to the home page' })).toHaveAttribute('href', '/')
  })

  it('a route that throws shows the error page', async () => {
    server.use(refreshAnswers(204).handler)
    expectConsole('error', /The page broke/)
    function Broken(): never {
      throw new Error('The page broke')
    }
    const router = createMemoryRouter([
      { path: '/', element: <Broken />, errorElement: <RouteError /> },
    ])

    render(
      <StrictMode>
        <AppProviders
          auth={createAuth()}
          queryClient={createTestQueryClient()}
          router={router}
          mantineEnv="test"
        />
      </StrictMode>,
    )

    expect(await screen.findByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reload the page' })).toBeInTheDocument()
  })
})
