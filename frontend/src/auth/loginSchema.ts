import { z } from 'zod'
import { LoginError } from './session'

/** The login form's fields. Both are required; the backend checks the rest. */
export const loginSchema = z.object({
  username: z.string().trim().min(1, 'Enter your username.'),
  password: z.string().min(1, 'Enter your password.'),
})

export type LoginValues = z.infer<typeof loginSchema>

/** What the login form says for each way a login can fail (spec 7). */
export function loginErrorMessage(error: Error): string {
  if (error instanceof LoginError && error.kind === 'invalid') return 'Wrong username or password.'
  if (error instanceof LoginError && error.kind === 'throttled') {
    const wait = error.retryAfter === null ? 'a minute' : seconds(error.retryAfter)
    return `Too many login attempts. Try again in ${wait}.`
  }
  // Unreachable, a 5xx, or anything unexpected: the user can only try again later.
  return "Can't reach the server. Try again in a moment."
}

function seconds(count: number): string {
  return count === 1 ? '1 second' : `${String(count)} seconds`
}
