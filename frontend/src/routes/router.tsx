import { Navigate, type RouteObject } from 'react-router'
import { RequireAuth } from '../auth/RequireAuth'
import { AppLayout } from '../components/AppLayout'
import { FullPageLoader } from '../components/FullPageLoader'
import { LoginPage } from './LoginPage'
import { NotFoundPage } from './NotFoundPage'
import { RouteError } from './RouteError'

/** Every route of the app, for createBrowserRouter (main.tsx) and createMemoryRouter (tests). */
export function createRoutes(): RouteObject[] {
  return [
    {
      errorElement: <RouteError />,
      // Shown while the first page's code loads. Without it the router warns on any first
      // load of a lazy page, such as a shared link to a task (ADR 0018).
      hydrateFallbackElement: <FullPageLoader />,
      children: [
        { path: '/login', element: <LoginPage /> },
        {
          path: '/',
          element: <RequireAuth />,
          children: [
            {
              element: <AppLayout />,
              children: [
                { index: true, element: <Navigate to="/tasks" replace /> },
                // The task pages load on demand, so the login page doesn't wait for them.
                {
                  path: 'tasks',
                  lazy: async () => ({
                    Component: (await import('./tasks/TaskListPage')).TaskListPage,
                  }),
                },
                {
                  path: 'tasks/new',
                  lazy: async () => ({
                    Component: (await import('./tasks/CreateTaskPage')).CreateTaskPage,
                  }),
                },
                {
                  path: 'tasks/:taskId',
                  lazy: async () => ({
                    Component: (await import('./tasks/TaskDetailPage')).TaskDetailPage,
                  }),
                },
                {
                  path: 'tasks/:taskId/edit',
                  lazy: async () => ({
                    Component: (await import('./tasks/EditTaskPage')).EditTaskPage,
                  }),
                },
              ],
            },
          ],
        },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ]
}
