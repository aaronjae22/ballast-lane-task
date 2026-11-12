import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { checkConsole, installConsoleGuard } from './console'

// jsdom lacks two browser APIs Mantine uses: media queries and element resize events.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

class ResizeObserverStub implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
window.ResizeObserver = ResizeObserverStub

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
