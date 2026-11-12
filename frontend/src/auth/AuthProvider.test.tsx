import { QueryClientProvider } from '@tanstack/react-query'
import { act, render, renderHook, screen } from '@testing-library/react'
import { StrictMode, type ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { logoutSucceeds, refreshAnswers } from '../test/handlers'
import { createTestQueryClient } from '../test/queryClient'
import { server } from '../test/server'
import { AuthProvider } from './AuthProvider'
import { createAuth } from './createAuth'
import { useApi, useAuth } from './useAuth'

function Status() {
  return <p>{useAuth().status}</p>
}

function renderProvider(children: ReactNode = <Status />) {
  const auth = createAuth()
  const queryClient = createTestQueryClient()
  render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AuthProvider auth={auth}>{children}</AuthProvider>
      </QueryClientProvider>
    </StrictMode>,
  )
  return { auth, queryClient }
}

describe('AuthProvider', () => {
  it('restores the session once on mount, even though StrictMode mounts twice', async () => {
    const refresh = refreshAnswers('access-1')
    server.use(refresh.handler)

    renderProvider()

    expect(screen.getByText('restoring')).toBeInTheDocument()
    expect(await screen.findByText('authenticated')).toBeInTheDocument()
    expect(refresh.count()).toBe(1)
  })

  it('shows anonymous when there is no session to restore', async () => {
    server.use(refreshAnswers(204).handler)

    renderProvider()

    expect(await screen.findByText('anonymous')).toBeInTheDocument()
  })

  it('empties the query cache when the session becomes anonymous', async () => {
    server.use(refreshAnswers('access-1').handler, logoutSucceeds())
    const { auth, queryClient } = renderProvider()
    await screen.findByText('authenticated')
    queryClient.setQueryData(['users', 'me'], { name: 'Alice Johnson' })

    await act(() => auth.session.logout())

    expect(screen.getByText('anonymous')).toBeInTheDocument()
    expect(queryClient.getQueryData(['users', 'me'])).toBeUndefined()
  })

  it('gives query hooks the API client', async () => {
    server.use(refreshAnswers(204).handler)
    const auth = createAuth()
    const queryClient = createTestQueryClient()

    const { result } = renderHook(() => useApi(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>
          <AuthProvider auth={auth}>{children}</AuthProvider>
        </QueryClientProvider>
      ),
    })
    await act(() => auth.session.restore())

    expect(result.current).toBe(auth.api)
  })
})

describe('useAuth', () => {
  it('outside the provider throws an error that says where it belongs', () => {
    // React 19 rethrows a render error to renderHook's caller without logging it.
    expect(() => renderHook(() => useAuth())).toThrow(/inside <AuthProvider>/)
  })
})
