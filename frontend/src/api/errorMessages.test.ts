import { describe, expect, it } from 'vitest'
import { describeError, fieldErrorsOf } from './errorMessages'
import { ApiError } from './errors'

function apiError(status: number, body: unknown = null, headers: Record<string, string> = {}) {
  return new ApiError(new Response(null, { status, headers }), body)
}

describe('describeError', () => {
  it('a 400 lists its messages, without the field names', () => {
    const error = apiError(400, {
      title: ['Must be 1 to 200 characters.'],
      due_date: ["Can't be in the past."],
    })

    expect(describeError(error)).toEqual({
      kind: 'invalid',
      title: "Some values weren't accepted",
      message: "Must be 1 to 200 characters. Can't be in the past.",
    })
  })

  it('a 400 without messages still says what to do', () => {
    expect(describeError(apiError(400, {})).message).toBe('Check the values and try again.')
  })

  it('a 401 that survived the refresh means the session has ended', () => {
    expect(describeError(apiError(401, { detail: 'Token is invalid' }))).toEqual({
      kind: 'unauthorized',
      title: 'Your session has ended',
      message: 'Log in again to continue.',
    })
  })

  it("a 403 shows the API's reason, which is written for a person", () => {
    const error = apiError(403, { detail: 'Only the owner or an admin can delete this task.' })

    expect(describeError(error)).toEqual({
      kind: 'forbidden',
      title: 'Not allowed',
      message: 'Only the owner or an admin can delete this task.',
    })
  })

  it('a 403 without a reason gets a general one', () => {
    expect(describeError(apiError(403)).message).toBe("You don't have permission to do that.")
  })

  it("a 404 doesn't say whether the task exists (ADR 0003)", () => {
    expect(describeError(apiError(404, { detail: 'No Task matches the given query.' }))).toEqual({
      kind: 'not_found',
      title: 'Task not found',
      message: "It may have been deleted, or it's no longer shared with you.",
    })
  })

  it("a 409 shows the API's reason for the refused transition", () => {
    const error = apiError(409, { detail: "Can't start a task that's done." })

    expect(describeError(error)).toEqual({
      kind: 'conflict',
      title: "The task's status changed",
      message: "Can't start a task that's done.",
    })
  })

  it('a 429 says when to try again, from Retry-After', () => {
    const error = apiError(429, { detail: 'Request was throttled.' }, { 'Retry-After': '42' })

    expect(describeError(error)).toEqual({
      kind: 'throttled',
      title: 'Too many requests',
      message: 'Try again in 42 seconds.',
    })
  })

  it.each([
    ['1', 'Try again in 1 second.'],
    [undefined, 'Try again in a minute.'],
  ])('a 429 with Retry-After %s says "%s"', (retryAfter, message) => {
    const headers: Record<string, string> =
      retryAfter === undefined ? {} : { 'Retry-After': retryAfter }

    expect(describeError(apiError(429, null, headers)).message).toBe(message)
  })

  it.each([500, 502, 503])("a %d means the server can't be reached", (status) => {
    expect(describeError(apiError(status))).toEqual({
      kind: 'unavailable',
      title: "Can't reach the server",
      message: 'Check your connection, then try again.',
    })
  })

  it("a request that got no answer means the server can't be reached", () => {
    // fetch rejects with a TypeError when there's no response at all.
    expect(describeError(new TypeError('Failed to fetch')).kind).toBe('unavailable')
  })

  it('any other error is unexpected', () => {
    expect(describeError(new Error('boom'))).toEqual({
      kind: 'unexpected',
      title: 'Something went wrong',
      message: 'Reload the page and try again.',
    })
    expect(describeError(apiError(415, { detail: 'Unsupported media type.' })).kind).toBe(
      'unexpected',
    )
  })
})

describe('fieldErrorsOf', () => {
  it("returns a 400's messages by field, including keys the form has no field for", () => {
    const body = { title: ['Must be 1 to 200 characters.'], non_field_errors: ['Nope.'] }

    expect(fieldErrorsOf(apiError(400, body))).toEqual(body)
  })

  it('is null for any other status, or a 400 whose body has another shape', () => {
    expect(fieldErrorsOf(apiError(403, { detail: 'No.' }))).toBeNull()
    expect(fieldErrorsOf(apiError(400, { detail: 'Not a field error.' }))).toBeNull()
    expect(fieldErrorsOf(apiError(400, 'plain text'))).toBeNull()
    expect(fieldErrorsOf(new TypeError('Failed to fetch'))).toBeNull()
  })
})
