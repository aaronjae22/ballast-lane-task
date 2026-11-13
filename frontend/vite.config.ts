import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// One origin in development too (spec 6, ADR 0006): the browser talks only to Vite, which
// forwards /api to Django, so the refresh cookie is first-party and there's no CORS.
// API_PROXY_TARGET is http://localhost:8000 on the host and http://backend:8000 in compose. It
// has no VITE_ prefix on purpose: Vite exposes VITE_* variables to the browser bundle.
// changeOrigin stays false, so Django sees Host: localhost:5173, which ALLOWED_HOSTS allows
// (ADR 0016).
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/ and https://vitest.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: false },
    },
  },
  build: {
    rolldownOptions: {
      output: {
        // The pages are split by route already (router.tsx). The libraries every page needs
        // go in chunks of their own, so no chunk passes Vite's 500 kB warning, and an app
        // change doesn't make browsers download React or Mantine again (ADR 0018).
        codeSplitting: {
          groups: [
            { name: 'mantine', test: /node_modules[\\/]@mantine[\\/]/ },
            {
              name: 'react',
              test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/,
            },
            { name: 'vendor', test: /node_modules[\\/]/ },
          ],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    // Only the unit and component tests: e2e/ is Playwright's (npm run e2e).
    include: ['src/**/*.test.{ts,tsx}'],
    // Vitest's default, a worker for nearly every core, makes the workers fight for the CPU: each loads
    // its own jsdom and the whole app, and a test that takes 0.5 s alone took over 5 s on a
    // busy machine. Half the cores runs the suite just as fast, with half the memory.
    maxWorkers: '50%',
    setupFiles: ['./src/test/setup.ts'],
    // Behind UTC, so a due date turned into midnight UTC shows the day before and a test
    // catches it (ADR 0018).
    env: { TZ: 'America/Los_Angeles' },
  },
})
