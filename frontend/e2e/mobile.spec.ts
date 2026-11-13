import { expect, logIn, test } from './console.ts'

// Spec section 8's narrowest width: the list is cards, its filters fold away, and a task
// opens and reads (ADR 0018).
test('alice opens the list and a task at 360 px', async ({ page }) => {
  await logIn(page, 'alice')

  const cards = page.getByRole('list', { name: 'Tasks' })
  await expect(cards).toBeVisible()
  await expect(page.getByRole('table', { name: 'Tasks' })).toHaveCount(0)
  await page.getByRole('button', { name: /^Filters/ }).click()
  await expect(page.getByRole('group', { name: 'Status' })).toBeVisible()

  const first = cards.getByRole('listitem').first().getByRole('link')
  const name = (await first.textContent()) ?? ''
  await first.click()

  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible()
  await expect(page.getByText('Owner', { exact: true })).toBeVisible()
})
