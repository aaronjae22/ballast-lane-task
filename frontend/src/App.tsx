import { MantineProvider, Title } from '@mantine/core'
import { theme } from './theme'

export default function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Title order={1}>Team Task Board</Title>
    </MantineProvider>
  )
}
