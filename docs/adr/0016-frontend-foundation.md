# ADR 0016: Frontend foundation

- Status: Accepted
- Date: 2026-11-12

## Context

Iteration 5 builds `frontend/`: login, a session that survives a reload, logout, and a responsive Mantine AppShell, on a client generated from the OpenAPI schema. Spec sections 6 and 8 and ADRs 0006, 0007 and 0014 fix the stack, the token model and the refresh race, but leave these questions open:
- How CI notices that the generated types are stale (ADR 0007), and what exactly it compares.
- Which router, and how protected routes wait for the silent refresh without flashing the login page.
- How the access token reaches the fetch wrapper, how one refresh at a time is enforced (ADR 0014), and what happens to requests in flight at logout.
- How "no console warnings" is checked, given that React StrictMode runs effects twice in development, and that with rotation a second refresh fails.
- What a fresh visit's silent refresh returns when there's no cookie at all. Chrome logs every failed request in the console, so a 401 there shows a red line on the login page.
- Which Node and TypeScript versions, and how they're pinned.
- How test-first commits pass a type-aware ESLint pre-commit hook.

The iteration 5 plan review settled these. They bind iteration 6 (query hooks, forms, tests) and iteration 7 (the build stage, nginx).

## Decision

- **The API contract is committed and checked.**
  - `frontend/src/api/generated/` holds `openapi.yml`, written by drf-spectacular with `--validate --fail-on-warn`, and `schema.d.ts`, written from it by openapi-typescript. Nothing in that folder is edited by hand.
  - `npm run gen:api` regenerates both. `gen:schema` runs the backend's `manage.py spectacular` through uv, setting `DJANGO_DEBUG=true` and `DJANGO_CACHE=locmem` itself, so it needs no secret key, Redis or database. `gen:types` needs only Node.
  - CI's `api-contract` job runs `npm run gen:api`, then `git diff --exit-code` on that folder. It fails on a backend change without regenerated files, on a hand edit, and on a generator upgrade that changes the output.
  - Lint, type check, tests, the build and the Docker image use the committed files and never need Python. Prettier, ESLint and pre-commit's whitespace hooks skip the folder, so no hook fights the generator.
- **Amendment to ADR 0014: a refresh without a cookie is 204.**
  - `POST /api/auth/token/refresh/` with no `refresh_token` cookie, or an empty one, answers 204 with no body and sets no cookie. "Not signed in" isn't an error, and a 401 would leave a red line in the console of every fresh visit and every reload after logout.
  - A cookie that is sent but is expired, blacklisted, malformed or the wrong type still gets 401, and the cookie is left alone, as ADR 0014 says.
  - Login with a wrong password stays 401.
- **The session lives outside React.**
  - `src/auth/session.ts` is plain TypeScript. It holds the access token in a closure: never React state, never `localStorage` or `sessionStorage`. `main.tsx` creates it once, before React renders.
  - React sees only the status (`restoring`, `authenticated`, `anonymous`, `unavailable`), through `useSyncExternalStore`. A token rotation doesn't change the status, so it doesn't render anything.
  - `restore()` is memoized for the session's lifetime: StrictMode's second effect run gets the same promise, and a load sends exactly one refresh. A 200 means `authenticated`. A 204 or 401 means `anonymous`. A network error, 5xx or 429 means `unavailable`, which shows "Can't reach the server" with a retry, not the login page.
- **One refresh at a time, with one retry.**
  - `refresh()` is single-flight: callers that arrive while a refresh is in flight wait for it and share its result (ADR 0014).
  - A refresh that gets 401 is retried once. Another tab may have just rotated the cookie, and the browser now holds the new one (ADR 0014's consequences). A second 401, or a 204, means `rejected`: the token is dropped and the status becomes `anonymous`.
  - A refresh that can't reach the server means `unavailable` and keeps the session, so a server blip doesn't log anyone out.
- **The fetch wrapper reads the token per request.**
  - openapi-fetch gets a custom `fetch`, `createAuthFetch`. It adds `Authorization: Bearer` from `session.getAccessToken()` as each request is sent, except to `/api/auth/`, which reads only the cookie.
  - It clones each request before sending it. On a 401 it waits for the single-flight refresh, then retries the request once with the new token. A second 401 is returned to the caller as is.
  - The underlying `fetch` is looked up on each call, not captured, so MSW intercepts it in tests.
- **Logout.**
  - Its order: the session bumps a generation counter and drops the token, waits for any refresh in flight (so the backend revokes the newest cookie), POSTs `/api/auth/logout/` ignoring errors, and becomes `anonymous`.
  - On `anonymous`, the provider cancels in-flight queries (TanStack Query aborts their fetches through `signal`) and clears the query cache, so the next user never sees the last one's data.
  - A request or refresh that started under an older generation is discarded: it can't refresh, retry or bring a token back after logout.
- **Router and protected routes.**
  - React Router in data mode (`createBrowserRouter`; `createMemoryRouter` in tests), without loaders. Route-level `errorElement`s give the error states.
  - The status starts as `restoring`, never `anonymous`. `RequireAuth` shows a full-page loader while restoring, so the login page never flashes. It redirects only on `anonymous`, to `/login` with the original location in `state.from`.
- **Server state.** Everything read from the API, the current user included, goes through TanStack Query hooks in `features/*/hooks/` (`useCurrentUser` is `['users', 'me']`). Login is a mutation hook in `src/auth/`. Forms use React Hook Form and Zod, starting with the login form.
- **Same origin in development.**
  - Vite's dev server proxies `/api` to `API_PROXY_TARGET`: `http://localhost:8000` on the host, `http://backend:8000` in compose. The name has no `VITE_` prefix, because Vite exposes `VITE_*` variables to the browser bundle.
  - The proxy keeps `changeOrigin: false`, so Django sees `Host: localhost:5173`, which `ALLOWED_HOSTS` allows. With `backend:8000` it would answer 400.
- **No console warnings.**
  - "No warnings" means nothing logged by the app, React, the router or Mantine. A failed login's 401 is a network line the browser logs, and it's expected.
  - In tests, any `console.error` or `console.warn` fails the test unless the test declares it. MSW fails on any request without a handler. The render helper always wraps in `<StrictMode>`.
  - In the browser, it's checked by hand at the end of each usable PR, under StrictMode.
- **Versions.**
  - **Node 24 LTS**, pinned exactly in `frontend/.nvmrc`. `package.json` sets `engines.node` to `>=24.22.0 <25`, and `.npmrc` sets `engine-strict=true`. CI's setup-node reads `.nvmrc`, and the Dockerfile uses the same version.
  - **TypeScript 5.9**, not npm's `latest` (7.x): typescript-eslint supports `<6.1`, and openapi-typescript peers on `^5`. Strict mode, no `any`.
- **Test first with typed stubs.** ESLint runs with type information, in pre-commit too. A test importing a module that doesn't exist yet would make that import `any` and fail the hook. So each `test:` commit adds the module's public shape as a stub whose bodies throw `not implemented`. Lint and type check pass at every commit, and the tests fail because the behaviour is missing, never because of a typo.

## Alternatives considered

- **Generating the schema in CI only, not committing it.** One less file, but contract changes vanish from PR diffs, and every frontend check would need Python.
- **Committing the types only.** The frontend would need no Python, but the drift check couldn't tell a stale schema from stale types.
- **Keeping 401 for a refresh without a cookie.** No backend change, but every fresh visit and every reload after logout would log a red line on the login page.
- **A non-httpOnly "signed in" hint cookie,** so the frontend could skip the refresh. A second cookie to keep in sync with the real one, for the same result.
- **The access token in React state or context.** Every rotation would re-render consumers, and a closure in the fetch wrapper could hold a stale token.
- **openapi-fetch middleware for the retry.** By `onResponse` the request body may already be consumed. A custom `fetch` can clone the request first.
- **Starting the silent refresh in an effect without memoizing it.** StrictMode would send two refreshes, and with rotation the second one fails.
- **Proactive refresh on a timer before the token expires.** Fewer 401s, but more moving parts. The spec refreshes on load and on a 401.
- **Logging the user out when a refresh can't reach the server.** Simpler, but a restart of the backend would sign everyone out.
- **TanStack Router.** Better typed routes, but not named by the spec, and React Router is the common default.
- **Route loaders that await the session.** They would couple routing to auth, and TanStack Query already handles loading states.
- **Node 26 LTS.** Supported a year longer, but this machine has Node 24, which is supported until April 2028, beyond this project.
- **TypeScript 7.** Faster, but the lint and type-generation tools don't support it yet.
- **ESLint without type information in pre-commit,** so failing tests could import missing modules. The hook and CI would then disagree, and rules like `no-floating-promises` would run only in CI.
- **Mantine's own form library.** It works, but ADR 0007 picked React Hook Form and Zod.

## Consequences

- **Iteration 6:**
  - Every new endpoint call is a query or mutation hook on the shared client. A backend change to the API shows up as a diff in `src/api/generated/` and fails `api-contract` until it's regenerated.
  - MSW handlers type their paths and bodies with the generated types. Tests that expect a console message must declare it.
- **Iteration 7:**
  - nginx must also proxy `/api` without rewriting `Host`, or set `ALLOWED_HOSTS` for it.
  - The frontend `build` stage uses the same Node version as `.nvmrc`.
- A Node or TypeScript upgrade is a change to `.nvmrc`, `engines`, the Dockerfile and this record.
- Upgrading to TypeScript 6.1 or 7 waits for typescript-eslint and openapi-typescript.
- A signed-out page load costs one request that answers 204.
- Logout doesn't revoke the access token (ADR 0014). The frontend drops it, and it expires within 5 minutes.
