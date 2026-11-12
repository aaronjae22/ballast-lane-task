import { z } from 'zod'
import type { LoginError } from './session'

/** The login form's fields. Both are required; the backend checks the rest. */
export const loginSchema = z.object({
  username: z.string(),
  password: z.string(),
})

export type LoginValues = z.infer<typeof loginSchema>

/** What the login form says for each way a login can fail (spec 7). */
export function loginErrorMessage(_error: LoginError): string {
  throw new Error('not implemented')
}
