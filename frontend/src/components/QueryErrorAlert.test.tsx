import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/errors'
import { renderUi } from '../test/render'
import { QueryErrorAlert } from './QueryErrorAlert'

function apiError(status: number, body: unknown = null) {
  return new ApiError(new Response(null, { status }), body)
}

describe('QueryErrorAlert', () => {
  it('shows what went wrong, and a retry that asks again', async () => {
    const onRetry = vi.fn()
    renderUi(<QueryErrorAlert error={new TypeError('Failed to fetch')} onRetry={onRetry} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent("Can't reach the server")
    expect(alert).toHaveTextContent('Check your connection, then try again.')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it.each([
    [403, { detail: 'Only the owner or an admin can edit this task.' }],
    [404, { detail: 'Not found.' }],
  ])('offers no retry for a %d, which answers the same every time', (status, body) => {
    renderUi(<QueryErrorAlert error={apiError(status, body)} onRetry={vi.fn()} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })
})
