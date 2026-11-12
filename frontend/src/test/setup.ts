import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { checkConsole, installConsoleGuard } from './console'

const original = { error: console.error, warn: console.warn }

beforeEach(() => {
  installConsoleGuard()
})

afterEach(() => {
  // Unmount first: a component can still warn while it unmounts.
  cleanup()
  try {
    checkConsole()
  } finally {
    console.error = original.error
    console.warn = original.warn
  }
})
