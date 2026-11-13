import { notifications } from '@mantine/notifications'

/** Reports an action that worked, on whatever page the user is on next (ADR 0018). */
export function notifySuccess(message: string): void {
  notifications.show({ color: 'green', message })
}
