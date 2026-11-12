import { useMantineTheme } from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'

/**
 * Whether the screen is at least Mantine's `sm` breakpoint wide. Read on the first render, so
 * a layout chosen from it doesn't flash the other one first (ADR 0018).
 */
export function useWideScreen(): boolean {
  const theme = useMantineTheme()
  return useMediaQuery(`(min-width: ${theme.breakpoints.sm})`, false, {
    getInitialValueInEffect: false,
  })
}
