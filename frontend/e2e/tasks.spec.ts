import type { Page } from '@playwright/test'
import { expect, logIn, test } from './console.ts'

// The happy path of ADR 0018 at desktop width, one role after another, on one task. A new
// title each run, so a rerun never finds the last run's task.
const title = `Playwright check ${String(Date.now())}`
const edited = `${title}, edited`

test.describe.configure({ mode: 'serial' })

test('alice creates a task assigned to bob, and edits it', async ({ page }) => {
  await logIn(page, 'alice')

  await page.getByRole('link', { name: 'New task' }).click()
  await page.getByRole('textbox', { name: 'Title' }).fill(title)
  await page.getByRole('combobox', { name: 'Assignee' }).click()
  await page.getByRole('option', { name: 'Bob Smith' }).click()
  await page.getByRole('button', { name: 'Create task' }).click()

  await expect(page.getByText('Task created.')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()

  await page.getByRole('button', { name: 'More' }).click()
  await page.getByRole('menuitem', { name: 'Edit' }).click()
  await page.getByRole('textbox', { name: 'Title' }).fill(edited)
  await page.getByRole('button', { name: 'Save changes' }).click()

  await expect(page.getByText('Changes saved.')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: edited })).toBeVisible()
})

test('bob, the assignee, starts and completes it', async ({ page }) => {
  await logIn(page, 'bob')
  await openTask(page, edited)

  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByText('Task started.')).toBeVisible()
  await page.getByRole('button', { name: 'Complete' }).click()
  await expect(page.getByText('Task completed.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reopen' })).toBeVisible()
})

test('the admin reopens and deletes it', async ({ page }) => {
  await logIn(page, 'admin')
  await openTask(page, edited)

  await page.getByRole('button', { name: 'Reopen' }).click()
  await expect(page.getByText('Task reopened.')).toBeVisible()
  await page.getByRole('button', { name: 'More' }).click()
  await page.getByRole('menuitem', { name: 'Delete…' }).click()
  await page
    .getByRole('dialog', { name: 'Delete task' })
    .getByRole('button', { name: 'Delete' })
    .click()

  await expect(page.getByText('Task deleted.')).toBeVisible()
  await expect(page).toHaveURL('/tasks')
})

// Through the list's title search, so the test finds the task on any page of the list.
async function openTask(page: Page, name: string): Promise<void> {
  await page.getByRole('searchbox', { name: 'Search titles' }).fill(name)
  await page.getByRole('link', { name }).click()
  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible()
}
