import { Stack, Text, Title } from '@mantine/core'

// A placeholder inside the AppShell, which pads it: task screens come in iteration 6.
export function HomePage() {
  return (
    <Stack gap="xs">
      <Title order={1}>Team Task Board</Title>
      <Text c="dimmed">You're signed in. Your tasks will appear here.</Text>
    </Stack>
  )
}
