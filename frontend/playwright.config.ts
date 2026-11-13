import { defineConfig, devices } from '@playwright/test'

// The real-browser console check (ADR 0018, spec section 2): one happy path in Chromium against
// the dev server, where StrictMode and React's development warnings are on. e2e/console.ts
// fails a test on any console error or warning, or any uncaught page error.
//
// It needs Postgres with the demo data (DATABASE_URL, as for runserver) and Redis, for the
// throttles and the Celery broker. Playwright starts runserver and Vite unless they're already
// running. The run logs in four times, under the login throttle of 5 a minute (spec section 7),
// so it runs on one worker with no retries.
const ci = Boolean(process.env.CI)

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  forbidOnly: ci,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /mobile\.spec\.ts/,
    },
    {
      name: 'mobile',
      // Spec section 8's narrowest width.
      use: { ...devices['Desktop Chrome'], viewport: { width: 360, height: 740 } },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
  webServer: [
    {
      command: 'uv run --directory ../backend python manage.py runserver 8000',
      url: 'http://localhost:8000/api/health/',
      env: { DJANGO_DEBUG: 'true' },
      reuseExistingServer: !ci,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !ci,
      timeout: 60_000,
    },
  ],
})
