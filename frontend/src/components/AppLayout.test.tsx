import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { apiUrl } from '../test/api'
import { refreshAnswers, signedInAs, users } from '../test/handlers'
import { renderApp } from '../test/render'
import { server } from '../test/server'

function header() {
  return screen.getByRole('banner')
}

async function signedInHome() {
  server.use(refreshAnswers('alice-token').handler, ...signedInAs())
  const app = renderApp()
  await screen.findByRole('heading', { name: 'Team Task Board' })
  return app
}

describe('the header', () => {
  it("shows a placeholder, then the signed-in user's name", async () => {
    let release: () => void = () => undefined
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      refreshAnswers('alice-token').handler,
      http.get(apiUrl('/api/users/me/'), async () => {
        await held
        return HttpResponse.json(users.alice)
      }),
    )
    renderApp()

    expect(await screen.findByLabelText('Loading your name')).toBeInTheDocument()
    release()

    expect(await within(header()).findByText('Alice Johnson')).toBeInTheDocument()
  })

  it('still renders, with a neutral label, when the user cannot be loaded', async () => {
    server.use(
      refreshAnswers('alice-token').handler,
      http.get(apiUrl('/api/users/me/'), () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
      ),
    )
    renderApp()

    expect(await within(await screen.findByRole('banner')).findByText('Signed in')).toBeVisible()
    expect(within(header()).getByRole('button', { name: 'Log out' })).toBeInTheDocument()
  })
})

describe('the navigation', () => {
  it('links to the home page', async () => {
    await signedInHome()

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
  })

  it('opens and closes with the burger on narrow screens', async () => {
    await signedInHome()
    // jsdom applies Mantine's hiddenFrom="sm" rule whatever the window width, so Testing
    // Library counts the burger as hidden, and a hidden element's accessible name is empty.
    // Its aria-label still finds it. On a narrow screen it's visible.
    const burger = screen.getByLabelText('Toggle navigation')

    expect(burger).toHaveAttribute('aria-expanded', 'false')
    await userEvent.click(burger)
    expect(burger).toHaveAttribute('aria-expanded', 'true')
    await userEvent.click(burger)
    expect(burger).toHaveAttribute('aria-expanded', 'false')
  })
})

describe('logging out', () => {
  it('signs out on the backend and goes to the login page', async () => {
    let logouts = 0
    server.use(
      http.post(apiUrl('/api/auth/logout/'), () => {
        logouts += 1
        return new HttpResponse(null, { status: 204 })
      }),
    )
    await signedInHome()
    await within(header()).findByText('Alice Johnson')

    await userEvent.click(screen.getByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(logouts).toBe(1)
  })

  it("never shows the previous user's name to the next one", async () => {
    server.use(
      http.post(apiUrl('/api/auth/logout/'), () => new HttpResponse(null, { status: 204 })),
    )
    await signedInHome()
    await within(header()).findByText('Alice Johnson')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Log out' }))
    await screen.findByRole('heading', { name: 'Log in' })
    await user.type(screen.getByLabelText('Username'), 'bob')
    await user.type(screen.getByLabelText('Password'), 'demo-password')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await within(await screen.findByRole('banner')).findByText('Bob Smith')).toBeVisible()
    expect(screen.queryByText('Alice Johnson')).not.toBeInTheDocument()
  })
})
