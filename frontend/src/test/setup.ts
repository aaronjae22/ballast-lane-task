import '@testing-library/jest-dom/vitest'
import { notifications } from '@mantine/notifications'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { checkConsole, installConsoleGuard } from './console'
import { server } from './server'

// jsdom lacks three browser APIs Mantine uses: media queries, element resize events, and
// scrollIntoView, which a Select calls to keep the highlighted option in view.
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

Element.prototype.scrollIntoView = () => undefined

// findBy* waits up to 3 s instead of 1 s. Task pages load lazily (ADR 0018), and the first test
// to open one also waits for Vite to transform its module, which can pass 1 s on a busy
// machine. A test that passes doesn't wait any longer.
configure({ asyncUtilTimeout: 3000 })

const original = { error: console.error, warn: console.warn }

beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
})

afterAll(() => {
  server.close()
})

beforeEach(() => {
  installConsoleGuard()
})

afterEach(() => {
  // Unmount first: a component can still warn while it unmounts.
  cleanup()
  // Mantine keeps notifications in a module-level store, which would outlive the test.
  notifications.clean()
  server.resetHandlers()
  try {
    checkConsole()
  } finally {
    console.error = original.error
    console.warn = original.warn
  }
})
