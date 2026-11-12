import { setupServer } from 'msw/node'

// The fake API every test talks to. Tests add handlers with server.use(); a request that no
// handler matches fails the test (ADR 0016).
export const server = setupServer()
