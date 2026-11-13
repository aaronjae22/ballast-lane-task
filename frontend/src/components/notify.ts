import { notifications } from '@mantine/notifications'
import { describeError } from '../api/errorMessages'

/** Reports an action that worked, on whatever page the user is on next (ADR 0018). */
export function notifySuccess(message: string): void {
  notifications.show({ color: 'green', message })
}

/** Reports an action the API refused or never answered, in the one mapping's words. */
export function notifyError(error: unknown): void {
  const { title, message } = describeError(error)
  notifications.show({ color: 'red', title, message })
}
