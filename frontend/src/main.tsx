import '@mantine/core/styles.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { AppProviders } from './AppProviders'
import { createAuth } from './auth/createAuth'
import { createQueryClient } from './queryClient'
import { createRoutes } from './routes/router'

// Created once, outside React, so StrictMode's double renders and effects can't make two
// sessions or two silent refreshes (ADR 0016).
const auth = createAuth()
const queryClient = createQueryClient()
const router = createBrowserRouter(createRoutes())

const root = document.getElementById('root')
if (!root) throw new Error('index.html has no #root element')

createRoot(root).render(
  <StrictMode>
    <AppProviders auth={auth} queryClient={queryClient} router={router} />
  </StrictMode>,
)
