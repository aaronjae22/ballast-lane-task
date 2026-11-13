import { expect, test as base, type Page } from '@playwright/test'

// Every test's page fails the test, once it's done, if the browser logged a console error or
// warning, or a page error went uncaught (spec section 2, ADR 0018). Vite's own lines and
// React's DevTools hint are debug and info messages, so they pass.
export const test = base.extend({
  page: async ({ page }, use) => {
    const problems: string[] = []
    page.on('console', (message) => {
      if (message.type() === 'error' || message.type() === 'warning') {
        problems.push(`console.${message.type()}: ${message.text()}`)
      }
    })
    page.on('pageerror', (error) => {
      problems.push(`uncaught: ${error.message}`)
    })
    await use(page)
    expect(problems, 'the browser console').toEqual([])
  },
})

export { expect }

/** Logs in as a demo user (README) and waits for the task list. */
export async function logIn(page: Page, username: 'alice' | 'bob' | 'admin'): Promise<void> {
  await page.goto('/login')
  await page.getByRole('textbox', { name: 'Username' }).fill(username)
  await page.getByRole('textbox', { name: 'Password' }).fill('demo-password')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Tasks' })).toBeVisible()
}
