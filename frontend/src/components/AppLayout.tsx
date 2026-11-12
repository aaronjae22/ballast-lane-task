import { AppShell, Burger, Button, Group, NavLink, Skeleton, Text } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { useMutation } from '@tanstack/react-query'
import { Link, Outlet, useMatch } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { useCurrentUser } from '../features/users/hooks/useCurrentUser'

/**
 * The frame around every signed-in page: a header with the user and logout, a navbar that
 * collapses behind a burger below the `sm` breakpoint, and the page itself. Works from 360 px:
 * below `xs` the app name gives its room to the user's name and the logout button.
 */
export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure(false)

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger
              opened={opened}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
              aria-label="Toggle navigation"
              aria-expanded={opened}
            />
            <Text fw={700} visibleFrom="xs">
              Team Task Board
            </Text>
          </Group>
          <Group gap="sm" wrap="nowrap" miw={0}>
            <CurrentUserName />
            <LogoutButton />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <NavItem to="/" label="Home" onNavigate={close} />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}

function NavItem({ to, label, onNavigate }: { to: string; label: string; onNavigate: () => void }) {
  const active = useMatch({ path: to, end: true }) !== null
  return <NavLink component={Link} to={to} label={label} active={active} onClick={onNavigate} />
}

function CurrentUserName() {
  const user = useCurrentUser()
  if (user.isPending) return <Skeleton height={16} width={120} aria-label="Loading your name" />
  // If /me fails the shell still works: the name is the only thing missing.
  return (
    <Text size="sm" truncate="end" maw={160}>
      {user.isError ? 'Signed in' : user.data.name}
    </Text>
  )
}

function LogoutButton() {
  const { logout } = useAuth()
  const mutation = useMutation({ mutationFn: logout })
  return (
    <Button
      variant="default"
      size="xs"
      loading={mutation.isPending}
      onClick={() => {
        mutation.mutate()
      }}
    >
      Log out
    </Button>
  )
}
