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
import { aTask, getTask } from '../test/tasks'
import { RouteError } from './RouteError'

const loginHeading = { name: 'Log in' }
const homeHeading = { name: 'Tasks' }

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

describe('the task routes', () => {
  it('/ goes to the task list', async () => {
    server.use(refreshAnswers('access-1').handler)

    const { router } = renderApp({ path: '/' })

    expect(await screen.findByRole('heading', { name: 'Tasks' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks')
  })

  // Opened directly, as from a shared link: each page loads lazily, without a console warning.
  it.each([
    ['/tasks', 'Tasks'],
    ['/tasks/new', 'New task'],
    ['/tasks/42', 'Task 42'],
    ['/tasks/42/edit', 'Edit task'],
  ])('%s shows its page', async (path, heading) => {
    server.use(refreshAnswers('access-1').handler, getTask(aTask({ id: 42 })).handler)

    renderApp({ path })

    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  })

  it('a signed-out link to a task goes to /login, remembering the task', async () => {
    server.use(refreshAnswers(204).handler)

    const { router } = renderApp({ path: '/tasks/42?from=email' })

    expect(await screen.findByRole('heading', loginHeading)).toBeInTheDocument()
    expect(router.state.location.state).toMatchObject({
      from: { pathname: '/tasks/42', search: '?from=email' },
    })
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
