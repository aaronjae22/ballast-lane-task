# Prompt 06: frontend foundation

- **Iteration:** 5 (frontend foundation)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/05-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** _PR links added after the run_

## Why the prompt is written this way

- **The workflow is unchanged, and the prompt says so explicitly.** Every commit still waits for my approval; a fresh session can't know that from earlier ones.
- **A new stack, so new places to go wrong.** The backend's habits (test first, small PRs, checks before every push) carry over to npm, ESLint and Vitest, and every new dependency needs a reason.
- **The API contract already exists.** The schema validates with no warnings (ADR 0014) so the frontend can generate its types from it. The open decision is how CI notices when the two drift apart, and that binds every later change, so it's an ADR question.
- **The auth flow has a known race.** With rotation and blacklisting, two refreshes with the same cookie can't both succeed, so ADR 0014 requires one refresh at a time. The prompt names it so the test for it comes first.
- **I test the app myself.** As soon as a page can be used, the agent stops and gives me steps to try it in a browser before going on. Green tests don't show a broken layout, a console warning or a login that feels wrong.
- **Docker doesn't run on this machine.** The compose service is proven in CI, and the manual checks use a host path: Vite's dev server proxying to `runserver`.

## The prompt

```text
You're building iteration 5 (Frontend foundation) of this repo. Before anything else, read AGENTS.md (especially the Frontend rules), CLAUDE.md, docs/spec.md (especially sections 2, 6, 8, 10, 11 and 13) and every file in docs/adr/ (especially 0006, 0007 and 0014). Iterations 0 to 4 are merged: the API is complete, the OpenAPI schema validates with no warnings, and seed_demo creates demo users (see the README). There is no frontend/ yet.

Goal: a frontend/ app where a demo user can log in, stay logged in across a page reload, and log out, inside a responsive Mantine AppShell, with the typed API client generated from the schema, and no warnings in the browser console. Task screens come in iteration 6.

IN SCOPE

1. frontend/: Vite + React + TypeScript (strict mode, no any), React StrictMode, ESLint (with the react-hooks rules) and Prettier, a router, Mantine, TanStack Query, and a test setup (Vitest, Testing Library, MSW; spec section 9). Node LTS, pinned. The npm scripts AGENTS.md already lists: dev, lint, typecheck, test, gen:api (plus build and format if you need them).
2. The API client: types generated from the backend's OpenAPI schema with openapi-typescript into src/api/ (never edited by hand), and an openapi-fetch client wrapped so every request carries the access token from memory.
3. Auth (spec section 6, ADRs 0006 and 0014): an AuthProvider context and a useAuth hook.
   - Login with username and password; the access token stays in memory only (never localStorage or sessionStorage); the refresh token is the backend's httpOnly cookie.
   - On page load, one silent refresh restores the session, so a reload doesn't log the user out.
   - A 401 triggers one refresh, then the request is retried once. Only one refresh runs at a time: requests that get a 401 while it's in flight wait for it (ADR 0014). If the refresh fails, the user is logged out.
   - Logout calls the backend, drops the token from memory and goes back to the login page.
   - 429 on login shows a friendly message (spec section 7).
4. Screens: a login page; an AppShell (header with the current user's name from /api/users/me/ and a logout button, navigation, responsive from 360 px wide); a placeholder home page inside the shell; routes that redirect to login when there's no session; and loading and error states for these.
5. One origin (spec section 6): Vite's dev server proxies /api to the backend, so the cookie (SameSite=Strict, Path=/api/auth/) is first-party. The target comes from configuration: localhost:8000 on the host, backend:8000 in compose.
6. Docker and CI: the frontend Dockerfile's dev target and a frontend service in compose (spec section 10); a CI job for frontend lint, type check, tests and build; ESLint and Prettier on frontend/ in pre-commit (spec section 11); hadolint already covers Dockerfiles. Update the Commands section of AGENTS.md.
7. Tests, written first: the auth provider (login, restore on load, logout), the 401 retry including several requests failing at once with exactly one refresh, the refresh failing, route protection, and the login form's errors (wrong credentials, 429, server down). MSW plays the API, using the generated types.

OUT OF SCOPE (don't build any of this, not even partially)

- Task list, filters, forms, assign and status actions, notifications for task actions (iteration 6)
- The frontend prod target, nginx and docker-compose.prod.yml (iteration 7)
- Backend changes, unless the frontend needs one to work at all. If it does, stop and tell me before planning it.

CONSTRAINTS

- Follow AGENTS.md (Frontend rules, Git, Scope) and the ADRs. If something here conflicts with them, stop and say so.
- Every new npm dependency gets a one-line reason in the plan. Prefer what spec section 8 and ADR 0007 already name.
- Where the spec and the ADRs don't decide something, don't guess. List it as a question in the plan, with the option you'd pick and why. At least:
  - Schema drift (spec section 8, ADR 0007: CI fails when the generated types are stale): is the schema file committed, generated in CI from the backend, or both, and what exactly does CI compare.
  - Which router, and how protected routes wait for the silent refresh on load without flashing the login page.
  - How "no console warnings" is checked: in tests (for example failing a test on any console warning or error) and in the browser, under StrictMode, which runs effects twice in development. A silent refresh started from an effect will run twice unless you design for it, and with rotation the second call fails.
  - How the access token reaches the fetch wrapper without React state causing extra renders or stale tokens, and what happens to queries in flight when the user logs out.
  - The Node version and how it's pinned, and whether this machine has it (check; don't install anything without telling me).
  - Whether any of this belongs in an ADR (0016) before the code, as in earlier iterations.
- No new backend dependencies.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer, not counting package-lock.json, generated API types and scaffolding the tool writes; say which files those are. Branches task/05-NN-short-name, from an up-to-date main. If an ADR is needed, it comes first, docs only.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first where there's behaviour: a test: commit with the failing tests, then a feat: commit that makes them pass. For each test: commit, show the test runner's summary lines and why the tests fail (a missing module or export, never a typo).
   - Show the public shape: the folder layout under src/, the AuthProvider's context value, the fetch wrapper, the routes, the npm scripts, the Vite proxy configuration, the compose service and the CI job. No bodies.
   - List every question and assumption, and every manual check (below) with the PR it comes after.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval. Don't commit on your own.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Manual checks in the browser. As soon as a PR makes something usable (at least: the first time the login page renders, the first time login works end to end, and at the end of the iteration), stop after its checks and before pushing, and give me:
   - the exact commands to start everything on this machine (Docker doesn't run here: the backend with runserver against the local Postgres, as in AGENTS.md, and the frontend with npm run dev through the proxy), and which demo user to log in as;
   - a short list of what to try, what I should see, and what to look for in the browser's console and network tab (the access token never in storage, the cookie's attributes, exactly one refresh on reload).
   Then wait for my go-ahead. If I report a problem, fix it in a new commit before the PR goes up.
4. Verify, and include the output of each command in your summary:
   - Backend, unchanged (cd backend): uv run ruff check . && uv run ruff format --check .; uv run lint-imports; DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run pytest
   - Frontend (cd frontend): npm ci; npm run lint; npm run typecheck; npm test; npm run build; and the schema drift check, whatever it ends up being
   - uv run --project backend pre-commit run --all-files
   - The compose frontend service is proven in CI only; say what CI runs for it.
5. Finish with a summary: what you created, every deviation from the spec and the ADRs and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

_Filled in after the run: what the output got right, what was wrong, and what I changed._
