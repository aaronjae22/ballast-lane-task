import type { RouteObject } from 'react-router'
import { RequireAuth } from '../auth/RequireAuth'
import { AppLayout } from '../components/AppLayout'
import { HomePage } from './HomePage'
import { LoginPage } from './LoginPage'
import { NotFoundPage } from './NotFoundPage'
import { RouteError } from './RouteError'

/** Every route of the app, for createBrowserRouter (main.tsx) and createMemoryRouter (tests). */
export function createRoutes(): RouteObject[] {
  return [
    {
      errorElement: <RouteError />,
      children: [
        { path: '/login', element: <LoginPage /> },
        {
          path: '/',
          element: <RequireAuth />,
          children: [
            { element: <AppLayout />, children: [{ index: true, element: <HomePage /> }] },
          ],
        },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ]
}
