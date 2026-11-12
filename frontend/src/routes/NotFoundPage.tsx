import { Button, Center, Stack, Text, Title } from '@mantine/core'
import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <Center h="100dvh" p="md">
      <Stack align="center" gap="sm" ta="center">
        <Title order={1}>Page not found</Title>
        <Text c="dimmed">There's no page at this address.</Text>
        <Button component={Link} to="/">
          Go to the home page
        </Button>
      </Stack>
    </Center>
  )
}
