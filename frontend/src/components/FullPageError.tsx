import { Button, Center, Stack, Text, Title } from '@mantine/core'

interface FullPageErrorProps {
  title: string
  message: string
  actionLabel: string
  onAction: () => void
}

/** The whole page when it can't be shown, with the one thing the user can do about it. */
export function FullPageError({ title, message, actionLabel, onAction }: FullPageErrorProps) {
  return (
    <Center h="100dvh" p="md">
      <Stack align="center" gap="sm" maw={420} ta="center">
        <Title order={2}>{title}</Title>
        <Text c="dimmed">{message}</Text>
        <Button onClick={onAction}>{actionLabel}</Button>
      </Stack>
    </Center>
  )
}
