# ADR 0007: React + TypeScript + Mantine, built to static files

- Status: Accepted
- Date: 2026-11-10

## Context

The brief asks to integrate the API with a frontend framework, with a responsive, user-friendly UI and cleanly organized components and state.

## Decision

- React + TypeScript with Vite. Node is used only to build; production serves static files from nginx.
- Mantine for components, layout, forms, date picker and notifications.
- TanStack Query for server state; an `AuthProvider` context is the only client state.
- React Hook Form + Zod for forms.
- A typed API client generated from the OpenAPI schema (openapi-typescript + openapi-fetch).
- Filters live in URL query parameters.

## Alternatives considered

- **Vue 3 + Pinia.** Equally capable; React with TypeScript is where I have more production experience.
- **Redux Toolkit.** Unneeded: nearly all state is server state, which TanStack Query already caches.
- **HTMX + Alpine.js.** Great for server-rendered apps, but the server returns HTML, so it doesn't consume a JWT-protected JSON API.
- **Tailwind + shadcn/ui.** More control, but the component code gets copied into the repo and has to be maintained as our own.
- **A Node backend-for-frontend.** No need: the browser talks to the Django API directly.

## Consequences

- Frontend and backend share one contract; CI fails when the generated types are stale.
- Mantine sets the visual style; heavy customization would mean working against it.
