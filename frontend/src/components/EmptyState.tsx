import { Paper, Stack, Text } from '@mantine/core'
import type { ReactNode } from 'react'

export interface EmptyStateProps {
  title: string
  message: string
  /** What the user can do next: a button or a link. */
  action: ReactNode
}

/** A page's "nothing here" state (spec section 8): what's missing, and what to do next. */
export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <Paper withBorder radius="md" p="xl">
      <Stack align="center" gap="xs" ta="center">
        <Text fw={600}>{title}</Text>
        <Text size="sm" c="dimmed">
          {message}
        </Text>
        {action}
      </Stack>
    </Paper>
  )
}
