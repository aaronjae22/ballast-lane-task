# ADR 0014: API conventions

- Status: Accepted
- Date: 2026-11-11

## Context

Iteration 3 builds the HTTP API from spec section 5 on the use cases and selectors of iterations 1 and 2. The spec and ADRs 0003, 0004, 0006, 0012 and 0013 fix the rules, the endpoints, the error mapping and the token model, but leave these questions open:
- How long the refresh token lives, when its cookie is `Secure`, and what logout and a failed refresh do with the cookie.
- What each endpoint returns, and what an error looks like.
- The page size, the ordering, and where tasks without a due date sort.
- What `/api/users/` and `/api/users/me/` return.
- When the shape of a request body is checked, compared with ADR 0012's order of checks, and what happens to fields an endpoint doesn't take.
- Whether the browsable API stays, and whether the schema and the docs are public.
- Which cache the throttles use in tests and on a host without Redis, and whether health is throttled.
- Which `Notifier` the use cases get until iteration 4 brings the Celery adapter.

The iteration 3 plan review settled these. They bind iteration 4 (the notifier), iteration 5 (the frontend's auth flow and generated client) and iteration 7 (deployment).

## Decision

- **Tokens and the refresh cookie.**
  - The access token lasts 5 minutes and comes in the response body (ADR 0006).
  - The refresh token lasts 1 day. Every refresh rotates it and blacklists the old one. Rotation restarts the day, so a user who comes back within a day stays signed in.
  - The cookie is `refresh_token`: httpOnly, `SameSite=Strict`, `Path=/api/auth/`, with a `Max-Age` equal to the refresh lifetime.
  - `Secure` is on outside local development, and local development means `DEBUG` is on. `DJANGO_REFRESH_COOKIE_SECURE` overrides it, for example to run the production image over plain http.
  - Login, refresh and logout don't read the access token, so an expired one can't block a refresh.
  - **A failed refresh is 401 and leaves the cookie alone.**
    - Two refreshes sent with the same cookie (two tabs, or several requests that got a 401 at once) race.
    - The first one rotates the token and sets the new cookie. The second one fails, because its token is now blacklisted.
    - If the failed response cleared the cookie and arrived last, it would delete the new cookie and sign the user out.
  - Logout blacklists the cookie's token if it's valid. It always answers 204 and clears the cookie, whether there was one or not.
  - Login answers a wrong password and an inactive user with the same 401 body, so it doesn't reveal which accounts exist.
- **Responses.**
  - Create is 201 with the task. PATCH and every action are 200 with the task. DELETE is 204 with no body. Login and refresh are 200 with `{"access": "..."}`. Logout is 204.
  - A task has `id`, `title`, `description`, `status`, `due_date`, `is_overdue`, `owner`, `assignee`, `completed_at`, `created_at` and `updated_at`.
    - `owner` and `assignee` are `{id, name}`, and `assignee` can be null.
    - After a write, the task is read back through `visible_tasks`, so a write returns the same shape as a read.
    - `is_overdue` is computed in the query from the same condition as the `overdue` filter. It judges "today" in `TIME_ZONE` (ADR 0012), not in the browser's time zone.
  - Errors are `{"detail": "..."}` for 401, 403, 404, 405, 409 and 429. Every 400 is `{"field": ["message", ...]}`, whether the input has the wrong shape or breaks a domain rule.
- **Users.**
  - `User.display_name` is the full name, or the username when the full name is empty. It's the one definition, used wherever a user is shown.
  - `/api/users/` lists the active users as `{id, name}`, ordered by username. It isn't paginated, because it feeds the assignee picker for a small team.
  - `/api/users/me/` returns `{id, username, name, is_admin}`, so the frontend can tell whether the user is an admin.
- **Pagination and ordering.**
  - The list uses DRF's `PageNumberPagination`: 20 tasks a page, and `?page_size=` up to 50.
    - DRF's own behaviour stands. An invalid `page_size` falls back to 20, a larger one is capped at 50, and a page past the end is 404.
    - `page_size` isn't a filter, so ADR 0013's "an invalid value is an error" doesn't apply to it.
  - `?ordering=` is part of `TaskFilter`, so an invalid value is 400, like any filter. It takes `due_date`, `created_at` and `status`, with `-` for descending and commas to combine them.
    - Tasks without a due date come last, in either direction.
    - `status` sorts in workflow order (to do, in progress, done), not alphabetically.
    - `id` breaks every tie, so two pages never overlap.
  - Without `?ordering=`, the soonest due date comes first, then `id`.
- **Request bodies.**
  - Serializers check only the shape: types and required fields (ADR 0012). The domain checks the title length, past due dates and active assignees.
  - A field the endpoint doesn't take is a 400. So `PATCH {"status": "done"}` fails instead of answering 200 and changing nothing.
  - **The shape is checked before the access checks**, because the serializer runs before the use case.
    - A malformed body is 400 even for a task the caller can't see. That reveals nothing, because the answer doesn't depend on the task.
    - This refines ADR 0012's order of checks: the body's shape first, then missing or not visible (404), then permission (403), then the rule (400 or 409).
- **JSON only.**
  - The API reads and writes JSON only. The browsable API is off, so `django_filters` isn't in `INSTALLED_APPS`: its templates only serve the browsable API's filter form.
  - With the JWT in a header, a browser can't sign in to the browsable API, so it would show nothing useful.
  - A cross-site HTML form can't send JSON, so a form posted to the cookie endpoints gets 415. Together with `SameSite=Strict`, that's a second barrier against CSRF on refresh and logout, and against login CSRF.
- **Throttling.**
  - DRF's throttles: 30 requests a minute for anonymous users, 120 for signed-in users, and 5 for login (the `auth` scope). Refresh and logout count as anonymous.
  - Production, compose and CI keep the Redis cache (spec section 7). A host without Redis sets `DJANGO_CACHE=locmem`, a cache inside the process. Any other value stops the app at startup.
  - Tests always use the in-process cache, emptied before each API test. No test inherits another test's counts, and no test can flush a real Redis.
  - **`/api/health/` isn't throttled.** Liveness shouldn't fail because the cache is down, or because other requests from the same address used up the anonymous limit. AGENTS.md allows public endpoints without throttling.
- **Schema and docs.**
  - `/api/schema/` and `/api/docs/` are public, throttled as anonymous. Swagger UI has to load before you can authorize, and the schema shows the API's shape, not its data.
  - Swagger UI loads from the CDN at a pinned version, not `@latest`. Its `persistAuthorization` option stays off, because it would keep the token in localStorage.
- **The notifier until iteration 4.** `LoggingNotifier` in `tasks/infrastructure/` logs each assignment once the transaction commits, as the port says adapters must. `tasks/api/wiring.py` builds it in one function, `notifier()`, which iteration 4 changes to return the Celery adapter.

## Alternatives considered

- **Clearing the cookie on a failed refresh.** Tidier when the token is simply dead, but it signs users out when two refreshes race.
- **Letting only one refresh per token run on the server.** That would avoid the race, but it needs a lock shared by every process. Running one refresh at a time in the frontend is simpler.
- **A 7-day refresh token.** Fewer logins, but a stolen cookie stays useful for a week.
- **`Secure` always on.** Simpler, but local development over http would lose the cookie.
- **A 400 or 401 for logout without a cookie.** Arguably more precise, but the client wants to be signed out either way.
- **Flat `owner_id` and `assignee_id`.** Smaller, but the frontend would need a lookup for every name, and an inactive owner isn't in `/api/users/`.
- **Computing overdue in the frontend.** It would use the browser's time zone, and it would be a third copy of the rule.
- **DRF's own `OrderingFilter`.** It silently ignores an invalid value, which ADR 0013 rules out for filters, and Postgres sorts null due dates first when descending.
- **Alphabetical status order.** It puts `done` first.
- **Ignoring unknown fields,** as DRF does by default. A client that sends `status` in a PATCH would get 200 and no change.
- **Checking the body after the access checks.** The view would have to load the task and check permission before the use case does: a second permission check outside the domain.
- **Keeping the browsable API.** Useless with JWT only, and it brings the form parsers with it.
- **Installing Redis on every development machine.** No code, but every host-run setup would need it.
- **Redis in tests.** Closer to production, but the tests would have to flush it, which would wipe a developer's local Redis.
- **Throttling health like every other endpoint.** Consistent, but a used-up limit or a Redis outage would mark a healthy container as unhealthy.
- **Schema and docs behind authentication.** Swagger couldn't load before Authorize, and iteration 5's type generation would need a token.
- **drf-spectacular-sidecar to serve Swagger UI locally.** It works offline, but it's one more dependency.
- **A notifier that does nothing.** Simpler, but an assignment would leave no trace before iteration 4.

## Consequences

- **Iteration 4:** the Celery adapter replaces `LoggingNotifier` in `wiring.notifier()`, and the logging adapter can go. The API tests replace the notifier with `RecordingNotifier`, so they don't change.
- **Iteration 5:**
  - The frontend runs one refresh at a time. Requests that get a 401 while a refresh is in flight wait for it, then retry with the new access token.
  - Another tab can still lose the race. It gets a 401 with the cookie untouched, and one retry with the new cookie succeeds.
  - The generated client sees JSON only, the task shape above and one error format.
  - `is_admin` decides which actions the frontend shows. The API still enforces the permission matrix.
- **Iteration 7:**
  - Throttles count per client address. Behind nginx every request comes from nginx, so DRF's `NUM_PROXIES` must be set, or all users share one limit.
  - Production must not use the in-process cache: its limits don't hold across processes.
- Logout doesn't revoke the access token. It stays valid until it expires, at most 5 minutes later, and the frontend drops it from memory.
- If Redis is down, every throttled request fails while health still answers 200.
- A malformed body gets its 400 before any 404, so a caller can learn that the body is wrong without learning anything about the task.
