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
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
