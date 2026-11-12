import { Center, Stack, Text, Title } from '@mantine/core'

// A placeholder: the login form comes in the next PR.
export function LoginPage() {
  return (
    <Center h="100dvh" p="md">
      <Stack align="center" gap="xs">
        <Title order={1}>Log in</Title>
        <Text c="dimmed">The login form is on its way.</Text>
      </Stack>
    </Center>
  )
}
