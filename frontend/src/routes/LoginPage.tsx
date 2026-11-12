import { zodResolver } from '@hookform/resolvers/zod'
import {
  Alert,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, type Path } from 'react-router'
import { loginErrorMessage, loginSchema, type LoginValues } from '../auth/loginSchema'
import { useAuth } from '../auth/useAuth'
import { useLogin } from '../auth/useLogin'
import { FullPageLoader } from '../components/FullPageLoader'

export function LoginPage() {
  const { status } = useAuth()
  const location = useLocation()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  // A signed-in user may be on their way here from a reload: show neither form nor flash.
  if (status === 'restoring') return <FullPageLoader />
  if (status === 'authenticated') return <Navigate to={destination(location.state)} replace />

  const onSubmit = handleSubmit((values) => {
    login.mutate(values)
  })

  return (
    <Center mih="100dvh" p="md">
      <Paper withBorder shadow="sm" radius="md" p="xl" w="100%" maw={400}>
        <form
          noValidate
          onSubmit={(event) => {
            void onSubmit(event)
          }}
        >
          <Stack>
            <div>
              <Title order={1} size="h2">
                Log in
              </Title>
              <Text c="dimmed" size="sm">
                Team Task Board
              </Text>
            </div>
            {login.error && (
              <Alert color="red" variant="light">
                {loginErrorMessage(login.error)}
              </Alert>
            )}
            <TextInput
              label="Username"
              autoComplete="username"
              error={errors.username?.message}
              {...register('username')}
            />
            <PasswordInput
              label="Password"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register('password')}
            />
            <Button type="submit" loading={login.isPending} fullWidth>
              Log in
            </Button>
          </Stack>
        </form>
      </Paper>
    </Center>
  )
}

// RequireAuth puts the page the user was going to in the location state (ADR 0016). History
// state can hold anything, so it's checked before use.
function destination(state: unknown): Partial<Path> {
  const from: unknown =
    typeof state === 'object' && state !== null && 'from' in state ? state.from : null
  if (typeof from !== 'object' || from === null) return { pathname: '/' }
  const { pathname, search, hash } = from as Partial<Record<keyof Path, unknown>>
  return {
    pathname: typeof pathname === 'string' ? pathname : '/',
    search: typeof search === 'string' ? search : '',
    hash: typeof hash === 'string' ? hash : '',
  }
}
