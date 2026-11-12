import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { expect, it } from 'vitest'
import App from './App'

it('renders the app inside Mantine under StrictMode', () => {
  render(
    <StrictMode>
      <App />
    </StrictMode>,
  )

  expect(screen.getByRole('heading', { name: 'Team Task Board' })).toBeInTheDocument()
  expect(document.documentElement).toHaveAttribute('data-mantine-color-scheme', 'light')
})
