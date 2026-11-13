import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { refreshAnswers, users } from '../../test/handlers'
import { renderApp } from '../../test/render'
import { server } from '../../test/server'
import {
  aPage,
  aTask,
  deleteTask,
  getTask,
  listTasks,
  summaryOf,
  updateTask,
} from '../../test/tasks'

// "Back to tasks" returns to the list the user came from, with its filters and page, through
// the task page, an edit and a delete. The list's search travels in the links' location state,
// not in app state (spec section 8: client state is the AuthProvider only).

const invoice = aTask({ id: 7, title: 'Send the October invoice', owner: summaryOf(users.alice) })
const renamed = { ...invoice, title: 'Send the November invoice' }
const filtered = '?status=to_do&page=2'

// The second of two pages of to-do tasks, holding the invoice.
function openFilteredList() {
  server.use(
    refreshAnswers('alice-token').handler,
    listTasks(aPage([invoice], { count: 25 })).handler,
    getTask(invoice, renamed).handler,
    updateTask(renamed).handler,
    deleteTask().handler,
  )
  const app = renderApp({ path: `/tasks${filtered}` })
  return app
}

async function openInvoice() {
  const card = within(await screen.findByRole('listitem'))
  await userEvent.click(card.getByRole('link', { name: 'Send the October invoice' }))
  await screen.findByRole('heading', { level: 1, name: 'Send the October invoice' })
}

async function edit() {
  await userEvent.click(screen.getByRole('button', { name: 'More' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Edit' }))
  return screen.findByRole('textbox', { name: 'Title' })
}

describe('Back to tasks', () => {
  it('from a task opened in a filtered list, goes back to that list and page', async () => {
    openFilteredList()

    await openInvoice()

    expect(screen.getByRole('link', { name: 'Back to tasks' })).toHaveAttribute(
      'href',
      `/tasks${filtered}`,
    )
  })

  it('still does after the task is edited and saved', async () => {
    openFilteredList()
    await openInvoice()
    const title = await edit()

    await userEvent.clear(title)
    await userEvent.type(title, 'Send the November invoice')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await screen.findByRole('heading', { level: 1, name: 'Send the November invoice' })
    expect(screen.getByRole('link', { name: 'Back to tasks' })).toHaveAttribute(
      'href',
      `/tasks${filtered}`,
    )
  })

  it('still does after an edit is cancelled', async () => {
    openFilteredList()
    await openInvoice()
    await edit()

    await userEvent.click(screen.getByRole('link', { name: 'Cancel' }))

    await screen.findByRole('link', { name: 'Back to tasks' })
    expect(screen.getByRole('link', { name: 'Back to tasks' })).toHaveAttribute(
      'href',
      `/tasks${filtered}`,
    )
  })

  it('deleting the task goes back to that list and page', async () => {
    const { router } = openFilteredList()
    await openInvoice()

    await userEvent.click(screen.getByRole('button', { name: 'More' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Delete…' }))
    await userEvent.click(
      within(await screen.findByRole('dialog', { name: 'Delete task' })).getByRole('button', {
        name: 'Delete',
      }),
    )

    await screen.findByText('Task deleted.')
    expect(router.state.location.pathname).toBe('/tasks')
    expect(router.state.location.search).toBe(filtered)
  })
})
