import { describe, expect, it } from 'vitest'
import { ApiError } from './api/errors'
import { createQueryClient } from './queryClient'

function retryRule() {
  const retry = createQueryClient().getDefaultOptions().queries?.retry
  if (typeof retry !== 'function') throw new Error('expected a retry function')
  return retry
}

function apiError(status: number): ApiError {
  return new ApiError(new Response(null, { status }), null)
}

describe('the query retry rule', () => {
  it('retries a server error up to twice', () => {
    const retry = retryRule()

    expect([0, 1, 2].map((failures) => retry(failures, apiError(503)))).toEqual([true, true, false])
  })

  it('retries a request that never got an answer', () => {
    expect(retryRule()(0, new TypeError('Failed to fetch'))).toBe(true)
  })

  it.each([400, 401, 403, 404, 409, 429])('never retries a client error (%i)', (status) => {
    expect(retryRule()(0, apiError(status))).toBe(false)
  })
})
