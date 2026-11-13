# Prompt 07: frontend features

- **Iteration:** 6 (frontend features)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/06-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** sixteen PRs, [#56](https://github.com/aaronjae22/ballast-lane-task/pull/56) ADR 0018 to [#71](https://github.com/aaronjae22/ballast-lane-task/pull/71) the browser console check: routes, error messages, URL filters, the task list with paging, ordering, search and filters, create, detail, the permission mirror, edit, transitions, assign and delete. Then two follow-ups: [#72](https://github.com/aaronjae22/ballast-lane-task/pull/72) an Unassigned option and a Back link that keeps the list's filters and [#73](https://github.com/aaronjae22/ballast-lane-task/pull/73) the transitions named in ADR 0018

## Why the prompt is written this way

- **The workflow is unchanged, and the prompt says so explicitly.** Every commit waits for my approval, and I test each usable screen in the browser before its PR goes up, as in iteration 5.
- **The server decides; the screen explains.** The API already enforces every rule and the permission matrix. The frontend's job is to show the user what they may do and to turn each error the API returns (a field error, a 403, a 409, a 429) into something they understand. Whether the form repeats a rule for faster feedback is a decision to make on purpose, not by accident.
- **The session rules are written down now.** ADR 0016 and ADR 0017 cover how tokens, refreshes and retries behave; iteration 6 adds mutations, and they have to follow those rules rather than invent their own.
- **Dates are a trap.** A due date is a plain day, and "overdue" depends on the server's time zone, so the browser's clock must never decide it.
- **"No console warnings" gets its explicit check here**, as spec section 2 says, so the prompt asks how it's proven, not just whether it's true.

## The prompt

```text
You're building iteration 6 (Frontend features) of this repo. Before anything else, read AGENTS.md (especially the Frontend rules), CLAUDE.md, docs/spec.md (especially sections 2, 3, 5, 7, 8 and 13) and every file in docs/adr/ (especially 0004, 0007, 0012, 0013, 0014, 0016 and 0017). Iterations 0 to 5 are merged: the API is complete and seed_demo fills it with demo data (see the README), and frontend/ has the generated API client, the session and auth flow, routing, the login page and the AppShell, with Vitest, Testing Library and MSW.

Goal: the task screens from spec section 8, so a demo user can do everything the API allows (list, filter, create, edit, assign, start, complete, reopen, delete) at mobile and desktop widths, with no warnings in the browser console.

IN SCOPE

1. The task list (spec sections 5 and 8):
   - Filters for status (several), due date range, overdue, assignee ("me" or a user) and title search, plus ordering and pagination, all kept in the URL's query parameters, so the back button works and a filtered view can be shared.
   - Each task shows its title, status, due date, overdue flag (from the API's is_overdue), owner and assignee, and the actions the current user may take.
   - Loading, empty and error states, and a sensible layout from 360 px wide.
2. Task detail and edit, and create (spec section 8): forms with React Hook Form and Zod. Create may set an assignee. Edit changes only title, description and due date (ADR 0004).
3. Actions: assign (from the active users, /api/users/), start, complete, reopen, and delete with a confirmation.
4. Which actions a user sees comes from the current user (is_admin from /api/users/me/) and the task's owner and assignee, following the permission matrix in spec section 3. The API still enforces it, so a 403 or 404 is still handled.
5. Errors, mapped once and reused: a 400 shows its messages on the matching form fields (the API keys them by field, ADR 0014); 403, 404 and 409 become a clear message; a 429 says when to try again from Retry-After (spec section 7); a network failure or 5xx says the server can't be reached.
6. Notifications for the result of each action (spec section 8), and confirmations for destructive actions.
7. Server state through TanStack Query hooks in features/tasks/hooks/ only (AGENTS.md). After a change, the data that changed is refetched or updated so the list, the detail and the counts agree. Mutations follow ADR 0016 and ADR 0017 (which requests retry, and how a 401 is handled).
8. Code splitting by route: the build is already over Vite's 500 kB warning.
9. Tests, written first, with MSW typed by the generated types: the list and its URL-driven filters and pagination, each form including server field errors, each action and its error cases (403, 404, 409, 429), what each role sees, and the empty, loading and error states.

OUT OF SCOPE (don't build any of this, not even partially)

- Backend changes, unless a screen can't work without one. If it can't, stop and tell me before planning it.
- The frontend prod target, nginx and docker-compose.prod.yml (iteration 7); the README and docs/ai-usage.md (iteration 8)
- Features the API doesn't offer (comments, attachments, bulk actions, an "unassigned" filter)

CONSTRAINTS

- Follow AGENTS.md (Frontend rules, Git, Scope) and the ADRs. If something here conflicts with them, stop and say so.
- Every new npm dependency gets a one-line reason in the plan.
- Where the spec and the ADRs don't decide something, don't guess. List it as a question in the plan, with the option you'd pick and why. At least:
  - Which rules the forms check before sending (for example title length, or no past due date) and which they leave to the API, and how the two stay consistent (the API's rules are in ADR 0012, and an overdue task's current due date must still be accepted on edit).
  - The date picker (Mantine's dates package would be a new dependency, with dayjs), and how a due date stays a plain YYYY-MM-DD day without the browser's time zone shifting it.
  - How the list's URL parameters map to the API's filters, and what an invalid parameter in a shared link does.
  - After each mutation: invalidate, update the cache, or optimistic update, and what the user sees while it runs.
  - Where actions live (list rows, the detail page, or both), and the layout of the list on mobile (table or cards).
  - How "no console warnings" is proven explicitly (spec section 2 puts the check in this iteration): tests already fail on console output, so what covers the real browser? For example a Playwright run on the host against runserver that fails on any console message, or a documented manual check. Say which, and what it needs on this machine.
  - Whether Playwright (optional in spec section 9) is worth adding now, and how it would run in CI without Docker on this machine.
  - Whether any of this belongs in an ADR (0018) before the code, as in earlier iterations.
- No new backend dependencies.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer, not counting package-lock.json and generated API types. Branches task/06-NN-short-name, from an up-to-date main. If an ADR is needed, it comes first, docs only.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first where there's behaviour: a test: commit with the failing tests, then a feat: commit that makes them pass. For each test: commit, show the test runner's summary lines and why the tests fail (a typed stub throwing "not implemented", a missing export, never a typo).
   - Show the public shape: the routes, the folder layout under src/features/tasks/, the hooks and their query keys, the components, the error mapping, and the URL parameters. No bodies.
   - List every question and assumption, and every manual check (below) with the PR it comes after.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval. Don't commit on your own.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Manual checks in the browser. As soon as a PR makes something usable (at least: the first time the task list shows real data, the first time I can create and edit a task, the first time the actions work, delete, and at the end of the iteration at 360 px and on desktop), stop after its checks and before pushing, and give me:
   - the exact commands to start everything on this machine (Docker doesn't run here: the backend with runserver against the local Postgres and seed_demo, as in AGENTS.md, and the frontend with npm run dev through the proxy), and which demo users to log in as (an owner, an assignee and the admin, so I can see each role);
   - a short list of what to try, what I should see, and what to look for in the browser's console and network tab.
   Then wait for my go-ahead. If I report a problem, fix it in a new commit before the PR goes up.
4. Verify, and include the output of each command in your summary:
   - Backend, unchanged (cd backend): uv run ruff check . && uv run ruff format --check .; uv run lint-imports; DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run pytest
   - Frontend (cd frontend): npm ci; npm run lint; npm run typecheck; npm test; npm run build (report the bundle sizes); and the API drift check (npm run gen:api, then git diff --exit-code -- src/api/generated/)
   - uv run --project backend pre-commit run --all-files
   - Whatever the explicit console check ends up being.
5. Finish with a summary: what you created, every deviation from the spec and the ADRs and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

**Plan.** The plan's decisions became ADR 0018 before any code. The plan review caught one conflict: to show only the actions a user may take, the frontend copies domain rules, which the Codex review rules flag as rules outside the domain. ADR 0018 now states their scope (display hints only; the API decides, and its errors are still handled), and `AGENTS.md` requires a frontend permissions test row for every permission change ([e5eacca](https://github.com/aaronjae22/ballast-lane-task/commit/e5eacca)).

**Build.** A Playwright run in Chromium fails on any console warning or error, in CI on every PR (#71), so the brief's "no warnings in the browser console" is checked, not assumed.

**Codex review.**
- #62, P2: a search still waiting to be written could undo Back or Clear filters. Fixed with the regression tests first ([747fdd8](https://github.com/aaronjae22/ballast-lane-task/commit/747fdd8)).
- #67, P1: the edit mutation's cache updates weren't tested. Tests that inspect the query cache after a save ([be013ed](https://github.com/aaronjae22/ballast-lane-task/commit/be013ed)).
- #69, P2: closing the Assign dialog while saving lost the pending state, so a reopened dialog could assign twice. Failing test first, then the save moved to the task's actions ([ab97e9e](https://github.com/aaronjae22/ballast-lane-task/commit/ab97e9e)).
- #71, P1, declined: Codex said the e2e login couldn't find the password field by its role. Playwright gives a password input the `textbox` role, and the CI job had logged in through that locator, so I replied with the evidence and changed nothing.

**Follow-ups.** In #72, Mantine's clear button is hidden from keyboard and screen-reader users, so both assignee pickers got an explicit Unassigned option, and Back to tasks now returns to the list with its filters. #73 records the status transitions as a third display copy in ADR 0018.
