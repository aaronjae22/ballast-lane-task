import { Center, Loader } from '@mantine/core'

/** The whole page while something it depends on loads, announced to screen readers. */
export function FullPageLoader() {
  return (
    <Center h="100dvh" role="status" aria-label="Loading">
      <Loader />
    </Center>
  )
}
