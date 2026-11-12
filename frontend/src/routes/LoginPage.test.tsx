import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { apiUrl } from '../test/api'
import { loginFails, loginSucceeds, loginUnreachable, refreshAnswers } from '../test/handlers'
import { renderApp } from '../test/render'
import { server } from '../test/server'

const homeHeading = { name: 'Tasks' }

async function openLoginPage(path = '/login') {
  server.use(refreshAnswers(204).handler)
  const app = renderApp({ path })
  await screen.findByRole('heading', { name: 'Log in' })
  return app
}

async function submit(username = 'alice', password = 'demo-password') {
  const user = userEvent.setup()
  if (username) await user.type(screen.getByLabelText('Username'), username)
  if (password) await user.type(screen.getByLabelText('Password'), password)
  await user.click(screen.getByRole('button', { name: 'Log in' }))
}

describe('the login form', () => {
  it('asks for both fields and sends nothing while either is empty', async () => {
    let requests = 0
    server.use(
      http.post(apiUrl('/api/auth/token/'), () => {
        requests += 1
        return HttpResponse.json({ access: 'access-1' })
      }),
    )
    await openLoginPage()

    await submit('', '')

    expect(await screen.findByText('Enter your username.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(requests).toBe(0)
  })

  it('hides the password as it is typed', async () => {
    await openLoginPage()

    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')
  })

  it('disables the button while the login is in flight', async () => {
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.post(apiUrl('/api/auth/token/'), async () => {
        await held
        return HttpResponse.json({ access: 'access-1' })
      }),
    )
    await openLoginPage()

    await submit()

    expect(screen.getByRole('button', { name: 'Log in' })).toBeDisabled()
    release()
    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
  })

  it('goes back to the page the user was going to', async () => {
    server.use(loginSucceeds())
    const { router } = await openLoginPage('/tasks?status=done')

    await submit()

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/tasks')
    expect(router.state.location.search).toBe('?status=done')
  })

  it('goes to the home page when opened directly', async () => {
    server.use(loginSucceeds())
    await openLoginPage('/login')

    await submit()

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
  })
})

describe('a failed login', () => {
  it('with wrong credentials says so', async () => {
    server.use(loginFails(401))
    await openLoginPage()

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong username or password.')
  })

  it('that was throttled says how long to wait', async () => {
    server.use(loginFails(429, { 'Retry-After': '42' }))
    await openLoginPage()

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many login attempts. Try again in 42 seconds.',
    )
  })

  it.each([
    ['is down', loginUnreachable()],
    ['answers 500', loginFails(500)],
  ])('when the server %s says it can not be reached', async (_case, handler) => {
    server.use(handler)
    await openLoginPage()

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Can't reach the server. Try again in a moment.",
    )
  })
})

describe('the login page', () => {
  it('sends a signed-in user to the home page', async () => {
    server.use(refreshAnswers('access-1').handler)

    renderApp({ path: '/login' })

    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
  })

  it('shows a loader, not the form, while the session restores', async () => {
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.post(apiUrl('/api/auth/token/refresh/'), async () => {
        await held
        return HttpResponse.json({ access: 'access-1' })
      }),
    )

    renderApp({ path: '/login' })

    expect(await screen.findByRole('status', { name: 'Loading' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Username')).not.toBeInTheDocument()
    release()
    expect(await screen.findByRole('heading', homeHeading)).toBeInTheDocument()
  })
})
