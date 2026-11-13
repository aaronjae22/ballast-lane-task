# ADR 0018: Frontend task screens

- Status: Accepted
- Date: 2026-11-12

## Context

Iteration 6 builds the task screens from spec section 8 (list, filters, detail, create, edit, assign, start, complete, reopen and delete) on the client, session and retry rules of ADRs 0016 and 0017. The spec and ADRs 0004, 0012, 0013 and 0014 fix the API, the rules and the error format, but leave these questions open:
- Which rules the forms check before sending, and how the browser stays consistent with the API. AGENTS.md says business rules live in `tasks/domain/` and nowhere else.
- How a due date stays a plain day when the browser and the server are in different time zones.
- How the list's URL parameters map to the API's filters, and what an invalid one in a shared link does.
- What a mutation does to the cached data, and what the user sees while it runs.
- Where the actions live, and how the list is laid out at 360 px.
- How the errors the API returns become messages.
- How "no browser console warnings" (spec section 2) is proven in a real browser, not only in tests.
- How the build gets under Vite's 500 kB chunk warning.

The iteration 6 plan review settled these. They bind every later change to the task screens, and iteration 7's build.

## Decision

- **Three frontend copies of domain rules, for display only.**
  - `src/features/tasks/permissions.ts` mirrors the permission matrix in spec section 3. It decides which actions a user sees, from `is_admin` (`/api/users/me/`) and the task's owner and assignee.
  - The title rule in `src/features/tasks/schemas.ts` mirrors ADR 0012: strip surrounding spaces, then 1 to 200 characters, with the API's message.
  - `permissions.ts` also mirrors the status transitions in spec section 3 (`_TRANSITIONS` in `backend/tasks/domain/task.py`): a task shows only the start, complete or reopen buttons its status allows. The API's 409 is still handled.
  - All three are display hints and early feedback. The API stays the authority. A 403, 409 or 400 is still handled on every screen, because a task can change between the read and the write.
  - Changing a rule or the permission matrix means changing both copies and both sets of tests: the backend's permission-matrix test and the frontend's `permissions.test.ts`. Both files say so in a comment.
  - Nothing else is checked in the browser. The past-due-date rule depends on the server's "today" in `TIME_ZONE` (ADR 0012), which the browser's today differs from for part of every day. So the picker has no `minDate`, and the API's 400 lands on the due date field. That's the reason ADR 0014 gives for not computing overdue in the browser. Whether an assignee is active is the API's to say: the picker offers only active users, and a user deactivated since gets the API's 400 on `assignee_id`.
- **Edit sends only what changed.** The PATCH holds only the fields the user changed (React Hook Form's dirty fields), and clearing the due date sends `null`. An overdue task's current date isn't re-sent unless the user changes it, and ADR 0012 accepts it when it is.
- **Due dates are plain days, end to end.**
  - The date picker is `@mantine/dates` with its peer `dayjs`. Its values are `YYYY-MM-DD` strings, which go to the API as they are. No `Date` object is built from a due date.
  - A due date is displayed by formatting `Date.UTC(year, month - 1, day)` in UTC, so no time zone can move it to the day before.
  - Overdue comes only from the API's `is_overdue`. Timestamps (`completed_at`, `created_at`, `updated_at`) are instants and show in the browser's time zone.
  - Vitest runs with `TZ=America/Los_Angeles`, behind UTC, so a test catches a shift.
- **The list's URL parameters are the API's filters.**
  - Same names and values: `status` (repeated), `due_after`, `due_before`, `overdue` (`true` or `false`), `assignee` (`me` or a user id), `search`, `ordering` (one of the six values) and `page`. Defaults (page 1, the API's default order) are left out.
  - Each parameter is validated on its own. An invalid one is dropped from the API query, and an alert lists what was ignored. The controls show the valid filters, and the next change rewrites the URL without the invalid ones. The API's 400 is still mapped, in case one gets through.
  - Changing a filter goes back to page 1 and adds a history entry, so Back undoes it. The title search waits 300 ms after typing stops and replaces the history entry while typing, so Back doesn't step through keystrokes.
  - A page past the end (the API's 404, for example after deleting the last task on the last page) says so and links to page 1.
  - An assignee not in `/api/users/` (inactive, or from a shared link) still shows: from `task.assignee`, or as "User #id".
- **After a mutation: invalidate, plus a guarded update. No optimistic updates.**
  - On success, the task the API returns replaces the cached detail, but only if that detail is already cached. Then every list is invalidated, so the rows, the count and the pages agree. Delete removes the detail and invalidates the lists.
  - A response that arrives after logout, when the cache has been cleared (ADR 0016), finds no detail to update, so it can't bring the previous user's task back.
  - On a 404, the detail is removed and the lists are invalidated. On a 403 or 409, both are invalidated: the task changed elsewhere, and the buttons should catch up.
  - While a mutation runs, its button shows a spinner and the task's other actions are disabled.
  - Mutations are never retried. A request that got no answer may have been applied, and a retry could create a task twice or send a second email. The fetch wrapper's single retry after a 401 is the only one (ADRs 0016 and 0017).
- **Actions and layout.**
  - One `TaskActions` component serves both the list rows (spec section 8's quick actions) and the detail page. It shows the transitions the user may make, and a menu with Assign, Edit and Delete as the user's role allows. Delete always asks for confirmation.
  - Routes: `/` redirects to `/tasks`. `/tasks` is the list, `/tasks/new` creates a task, `/tasks/:taskId` shows one, and `/tasks/:taskId/edit` edits it.
  - From Mantine's `sm` breakpoint up, the list is a table; below it, a stack of cards. One of the two is rendered (`useMediaQuery`, read on the first render), never both. Below `sm` the filters fold behind a "Filters" button.
  - No icon library: the buttons and menus use text labels.
- **Errors are mapped once.**
  - `src/api/errorMessages.ts` turns any error into a kind, a title and a message, and every screen uses it.
  - A 400's field errors go on the matching form fields (the API keys them by field, ADR 0014). Keys the form has no field for go in an alert above the form.
  - 403, 404 and 409 get a fixed title, with the API's `detail` as the message. Each one is written for a person.
  - A 429 says when to try again, from `Retry-After`.
  - A network failure or a 5xx says the server can't be reached.
  - A 401 that survives the fetch wrapper's refresh signs the session out, and `RequireAuth` goes to the login page.
  - Results of actions are reported with `@mantine/notifications`.
- **Code splitting.** The four task pages load through React Router's route `lazy`. The root route has a `hydrateFallbackElement`, because without one the router logs a warning while the first lazy page loads. If the main chunk is still over 500 kB, the build splits the vendor code into its own chunks.
- **No console warnings, proven in a real browser.**
  - Vitest's console guard stays (ADR 0016).
  - Playwright (`@playwright/test`) runs one happy path in Chromium against the dev server, so StrictMode and React's development warnings are on. Any console error or warning, or any uncaught page error, fails the run.
    - At desktop width: alice creates a task assigned to bob and edits it, bob starts and completes it, and the admin reopens and deletes it.
    - At 360 px: alice opens the list and a task.
  - `npm run e2e` runs it. Playwright starts runserver and Vite unless they're already running. On a host it needs Postgres with the demo data, Redis, and Chromium installed by Playwright.
  - CI runs it in its own job, with Postgres and Redis as service containers, so it needs no Docker on the development machine.
  - It uses one worker and no retries, and it logs in four times, under the login throttle of 5 a minute (spec section 7).
  - The manual check in an Incognito window stays at the end of each usable PR, because browser extensions add their own console lines.

## Alternatives considered

- **No frontend copy of the permission matrix,** showing every action and letting the API refuse. The rule would live in one place, but every user would see buttons that answer 403.
- **Asking the API which actions are allowed,** with a field on each task. One source of truth, but it's a backend change for a display hint the matrix already gives.
- **Checking past due dates in the browser.** Faster feedback, but wrong for part of every day wherever the browser's time zone isn't the server's.
- **Sending every field on edit.** Simpler, but it re-sends an overdue task's date on every save. ADR 0012 accepts that, but it makes every edit depend on that rule.
- **`Date` objects for due dates.** `new Date('2026-11-12')` is midnight UTC, which is the day before in any time zone west of UTC.
- **Passing an invalid URL parameter to the API** and showing its 400. The whole list would fail over one bad parameter in a shared link.
- **Optimistic updates.** Instant, but a 403 or 409 would undo what the user just saw, and a filtered list would have to re-filter in the browser.
- **Updating the cache only, without invalidating the lists.** One request fewer, but a status change can move a task out of a filtered list and change the count.
- **Retrying mutations on a 5xx.** It hides a server blip, but it can duplicate a create or an email.
- **Actions only on the detail page.** Less code, but spec section 8 asks for quick actions in the list.
- **A table at every width,** scrolling sideways on a phone. One layout, but six columns don't fit in 360 px.
- **Rendering both the table and the cards and hiding one with CSS.** No media query in JavaScript, but double the DOM, and duplicates in every test query.
- **`@mantine/modals` for the confirmation.** Its confirm helper is convenient, but the core `Modal` does the job without another dependency.
- **A documented manual console check only.** Nothing to install, but nothing repeats it after the last manual check.
- **Playwright against the compose stack in CI.** The stack already runs there, but the login throttle would count the compose job's own logins too, and the command would differ from the one on a host.

## Consequences

- A change to the permission matrix, the status transitions or the title rule touches two places, the domain and the frontend copy, and both test suites. AGENTS.md's testing rules say so.
- The UI can show an action the API then refuses, if the task changed since it was loaded. The error is explained and the data refetched.
- A due date in the past is reported after a round trip, not as the user picks it.
- After every mutation the lists refetch, at the cost of one request per visible list.
- `npm run e2e` needs a running database with the demo data and Redis. A second run within a minute can hit the login throttle.
- Iteration 7's build keeps the route-level chunks. nginx has to serve them like any other static file.
