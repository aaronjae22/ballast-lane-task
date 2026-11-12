# Team Task Board: specification

The written specification this project is built from. Every iteration in section 13 is one branch and one pull request. The reasons behind the main choices are in [`docs/adr/`](adr/).

## 1. User story

A small team shares a task board.

- As a **team member**, I create tasks, assign them to a teammate, and track them to done.
- As an **assignee**, I see what's on my plate, what's due soon and what's overdue. I get an email when a task is assigned to me and a reminder the day before it's due.
- As an **admin**, I can see and manage every task.

## 2. Requirements traceability

| Requirement from the brief | How it's met | Iteration |
|---|---|---|
| CRUD tasks | Use cases on the write path, selectors on the read path, DRF ViewSet | 1, 2, 3 |
| Assign tasks, mark completed | `assign`, `start`, `complete`, `reopen` action endpoints | 1, 3 |
| Filter by status and due date | django-filter: `status`, `due_after`, `due_before`, `overdue`, `assignee` | 2, 3 |
| JWT authentication | simplejwt; access token in the response body, refresh token in an httpOnly cookie | 3 |
| Pagination | DRF `PageNumberPagination`, `page_size` adjustable up to 50 | 3 |
| PostgreSQL schema for tasks and users | Custom `User` + `Task` with indexes | 0, 2 |
| pytest, ≥80% coverage | pytest-django + pytest-cov, `fail_under = 80` enforced in CI | 0 onward |
| Dockerfile + docker-compose for app and database | Multi-stage Dockerfiles (dev + prod targets); compose runs the whole stack with one command (section 10) | 0, 4, 5, 7 |
| README with setup + key decisions | README + `docs/adr/` | Throughout, final in 8 |
| Swagger docs | drf-spectacular at `/api/docs/` ([ADR 0005](adr/0005-api-docs-drf-spectacular.md)) | 3 |
| pyproject (uv), pre-commit, good practices | uv, ruff, pre-commit, import-linter, hadolint, GitHub Actions CI | 0 |
| Rate limiting | DRF throttles stored in Redis; stricter scope on login | 3 |
| Background processing | Celery + Redis + Beat; Mailpit to view emails | 4 |
| Frontend: responsive, CRUD, clean structure | React + TypeScript + Mantine, feature folders, TanStack Query | 5, 6 |
| Seeded data and demo credentials | `manage.py seed_demo`, run automatically by compose; credentials in README | 4 |
| No browser console warnings | React StrictMode on; explicit check in 6 | 6 |
| GenAI: prompt, output, validation, corrections, edge cases, performance | [`docs/ai-usage.md`](ai-usage.md), [`docs/ai/prompts/`](ai/prompts/), Codex PR reviews (section 12) | Throughout, final in 8 |

## 3. Domain

### Task

| Field | Rules |
|---|---|
| `title` | Required, 1–200 characters |
| `description` | Optional |
| `status` | `to_do`, `in_progress`, `done` |
| `due_date` | Optional date; can't be set to a date in the past (tasks already overdue stay valid) |
| `owner` | Whoever created the task; never changes |
| `assignee` | Optional, also when the task is created; must be an active user |
| `completed_at` | Set when completed, cleared when reopened |
| `created_at`, `updated_at` | Automatic |

**Overdue** is computed (due date passed and status isn't done), never stored.

### Status transitions

| Action | From | To | Side effect |
|---|---|---|---|
| start | `to_do` | `in_progress` | none |
| complete | `to_do`, `in_progress` | `done` | sets `completed_at` |
| reopen | `done` | `to_do` | clears `completed_at` |

Any other transition raises `InvalidTransition` (HTTP 409).

### Permissions

| Action | Owner | Assignee | Admin | Anyone else |
|---|---|---|---|---|
| View | ✓ | ✓ | ✓ | 404 |
| Edit title, description, due date | ✓ | 403 | ✓ | 404 |
| Assign, reassign, unassign | ✓ | 403 | ✓ | 404 |
| Start, complete, reopen | ✓ | ✓ | ✓ | 404 |
| Delete | ✓ | 403 | ✓ | 404 |

A task you can't see returns 404, not 403, so the API doesn't reveal that it exists.

Any signed-in user can create a task and becomes its owner, with or without an assignee.

### Assignment email

The assignee gets an email only when the assignee changes to someone other than the person making the change: a task created with someone else as its assignee, or assigned or reassigned to someone else. There's no email for self-assignment, for unassigning, or for reassigning a task to the person who already has it.

## 4. Architecture

The dependency rule: business rules know nothing about Django, HTTP or Celery. It's applied strictly where rules live (writes), with plain Django where there are none (reads). See [ADR 0002](adr/0002-architecture-strict-writes-plain-reads.md).

- **Writes:** `api` → use case (`application`) → domain `Task` (`domain`). Use cases talk to the outside world only through ports: `TaskRepository`, `UserLookup`, `Notifier`, `Clock`. The ORM and Celery implement them in `infrastructure`.
- **Reads:** `api` → `selectors.py` → QuerySet → django-filter + DRF pagination. The only rule on reads ("which tasks can this user see") is one selector function.
- **Composition root:** `tasks/api/wiring.py` builds use cases with real adapters; tests build them with in-memory fakes.
- **Error mapping** (custom DRF exception handler): `NotAllowed` → 403, `TaskNotFound` / not visible → 404, `InvalidTransition` → 409, `DomainValidationError` → 400.
- **Enforced by import-linter in CI:**
  - `tasks.domain` imports nothing from Django, DRF or Celery
  - `tasks.application` imports only `tasks.domain`
  - `tasks.domain` and `tasks.application` never import `tasks.infrastructure` or `tasks.api`
- Django conventions (`models.py`, `admin.py`, `migrations/`) stay where Django expects them and count as infrastructure.

```
backend/
  config/               settings, urls, celery app, wsgi
  accounts/             custom User, JWT views (refresh cookie), users endpoints, seed_demo
  tasks/
    domain/             Task, Status, rules, errors          (pure Python)
    application/        use cases + ports (Protocols)        (imports domain only)
    infrastructure/     ORM repository, Celery notifier, Celery tasks, clock
    api/                serializers, views, filters, permissions, wiring, urls
    selectors.py        read queries returning QuerySets
    models.py, admin.py, migrations/, templates/emails/
  tests/
    unit/               domain + use cases with fakes, no database
    integration/        repository, selectors, Celery adapters (Postgres)
    api/                endpoints: auth, permissions, filters, pagination, throttling
```

## 5. API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/token/` | Returns access token; sets refresh cookie. Throttle scope `auth` |
| POST | `/api/auth/token/refresh/` | Reads refresh cookie; rotates it |
| POST | `/api/auth/logout/` | Blacklists refresh token, clears cookie |
| GET | `/api/users/` | Active users (id, name) for the assignee picker |
| GET | `/api/users/me/` | Current user |
| GET, POST | `/api/tasks/` | Paginated. Filters: `status` (multiple), `due_after`, `due_before`, `overdue`, `assignee` (`me` or id), `search` (title). Ordering: `due_date`, `created_at`, `status`. POST accepts an optional `assignee_id` |
| GET, PATCH, DELETE | `/api/tasks/{id}/` | PATCH for title, description, due date only |
| POST | `/api/tasks/{id}/assign/` | Body: `{"assignee_id": int \| null}` |
| POST | `/api/tasks/{id}/start/`, `/complete/`, `/reopen/` | Status transitions |
| GET | `/api/health/` | Liveness for Docker and Cloud Run |
| GET | `/api/schema/`, `/api/docs/` | OpenAPI 3 schema and Swagger UI |

Action endpoints map one-to-one to use cases, each with its own permission rule and side effect, and they show up clearly in Swagger. PATCH never changes status or assignee. See [ADR 0004](adr/0004-action-endpoints.md).

## 6. Authentication

See [ADR 0006](adr/0006-jwt-refresh-cookie-same-origin.md).

- simplejwt with the `token_blacklist` app. The access token is short-lived (5 minutes) and lives only in memory on the frontend. The refresh token is in an httpOnly, `SameSite=Strict` cookie scoped to `/api/auth/`, `Secure` outside local development, rotated on every refresh.
- The frontend refreshes silently on load and on a 401, then retries the request once.
- nginx serves the React build and proxies `/api` to Django (Vite's proxy does the same in development), so it's one origin: no CORS, and the cookie is first-party.
- CSRF on the refresh endpoint: `SameSite=Strict` blocks cross-site sends, and the response body (the new access token) can't be read cross-origin anyway.

## 7. Rate limiting and background jobs

- **Throttles** (DRF, stored in the Redis cache so limits hold across processes): anonymous 30/min, authenticated 120/min, `auth` scope 5/min. Returns 429 with `Retry-After`; the frontend shows a friendly message.
- **Assignment email** (only when the assignee changes to someone else; see section 3): the `Notifier` adapter queues a Celery task inside `transaction.on_commit`, so a rolled-back assignment never sends an email.
- **Due-tomorrow reminders:** Celery Beat runs a daily task that emails each assignee a digest of their tasks due tomorrow.
- **Mailpit** in docker-compose catches all email locally (web UI on port 8025).
- **Demo data:** `manage.py seed_demo` is idempotent. It creates an admin, three users with known passwords, and about 25 tasks across every status and due-date bucket (overdue, today, tomorrow, next week, none), so every filter shows results.

## 8. Frontend

See [ADR 0007](adr/0007-frontend-react-typescript-mantine.md).

- Vite + React + TypeScript, React StrictMode.
- **UI kit:** Mantine (AppShell for the responsive layout, tables, forms, date picker for due dates, notifications, modals for confirmations).
- **Server state:** TanStack Query. **Client state:** an `AuthProvider` context only. Redux Toolkit isn't needed because nearly all state is server state.
- **API client:** types generated from the OpenAPI schema (openapi-typescript) with a typed fetch client (openapi-fetch). Backend and frontend share one contract; a CI step fails if the generated types are stale.
- **Forms:** React Hook Form + Zod, wired to Mantine inputs.
- **Filters** live in URL query parameters, so the back button works and filtered views can be shared.
- **Screens:** login; task list (filters, pagination, quick actions); task detail/edit; create task. Responsive from 360 px wide up.
- **Every screen** has loading, empty and error states; destructive actions ask for confirmation; notifications report results.

```
frontend/src/
  api/              generated schema types, client, auth-aware fetch wrapper
  auth/             AuthProvider, useAuth, refresh logic
  features/tasks/   components/, hooks/ (useTasks, useTaskMutations), schemas.ts, filters.ts
  components/       shared UI
  routes/           pages and route definitions
  test/             MSW handlers, render helpers
```

## 9. Testing strategy

- **Test first on the write path:** each domain rule and use case gets a failing test committed first (`test:` commit), then the code (`feat:` commit). The git history shows it.
- **Unit:** domain + use cases with in-memory fakes; no database; aim for 100% here.
- **Integration:** ORM repository, selectors and Celery adapters against Postgres (`django_capture_on_commit_callbacks` for the on-commit behavior).
- **API:** the permission matrix as a parametrized test, filters, pagination, throttling, auth flow, error mapping.
- **Performance:** query-count tests on the list and detail endpoints (`django_assert_max_num_queries`) to catch N+1 queries; `select_related` for owner and assignee; filter indexes checked with `EXPLAIN`.
- **Frontend:** Vitest + Testing Library + MSW for components and hooks. Optional: one Playwright run through log in → create → assign → complete.
- **Coverage gate:** 80% minimum enforced by pytest-cov in CI; target 90%+.

## 10. Docker

See [ADR 0009](adr/0009-docker-multi-stage-one-image.md).

- **`backend/Dockerfile`, multi-stage:**
  - `base`: `python:3.13-slim` with uv copied from its official image
  - `deps`: `uv sync --frozen --no-install-project`, a cached layer that only rebuilds when `uv.lock` changes
  - `dev` target: dev dependencies, `runserver` with reload, source mounted as a volume
  - `prod` target: no dev dependencies, non-root user, `collectstatic`, gunicorn
  - The same image runs the API, the Celery worker and Celery Beat with different commands.
- **`frontend/Dockerfile`, multi-stage:** `dev` target (Vite dev server) → `build` stage → `prod` target (nginx serving `dist/` and proxying `/api` to the backend).
- **`docker-compose.yml` (local):** `db` (postgres:17, healthcheck, named volume), `redis` (healthcheck), `backend`, `worker`, `beat`, `mailpit`, `frontend`. Services wait for healthy dependencies (`depends_on: condition: service_healthy`). The backend entrypoint runs `migrate`, then `seed_demo` when `SEED_DEMO=true` (the local default).
- **Works without a `.env` file:** compose has sensible defaults; `.env.example` documents the overrides.
- **One-command demo:** `docker compose up --build`, then open http://localhost:5173 and log in with the README credentials. Swagger at http://localhost:8000/api/docs/, Mailpit at http://localhost:8025.
- **`docker-compose.prod.yml` override:** runs the `prod` targets locally (gunicorn + nginx on http://localhost:8080) to prove the production images work.
- **Hygiene:** a `.dockerignore` per image, hadolint in pre-commit, CI builds both `prod` images.

## 11. Tooling and repo layout

See [ADR 0008](adr/0008-python-tooling-uv-ruff-precommit.md).

- **Backend:** Python 3.13, Django 5.2 LTS (versions confirmed against every dependency in iteration 0), uv with `pyproject.toml` and committed `uv.lock`, ruff (lint + format), import-linter.
- **Frontend:** Node LTS for building only, ESLint (with react-hooks rules) + Prettier.
- **pre-commit:** local hooks that call `uv run ruff ...` so pre-commit, the editor and CI use the same ruff version; uv lock check; hadolint; ESLint + Prettier on `frontend/`.
- **CI (GitHub Actions):** lint, import-linter, backend tests with coverage gate (Postgres + Redis service containers), frontend lint + type check + tests, Docker builds.
- **Commits:** Conventional Commits. PRs are merged with merge commits, not squashed, so the test-first history and the split between AI-made and human commits stay visible.

```
/
  backend/              Django project (own Dockerfile, pyproject.toml, uv.lock)
  frontend/             React app (own Dockerfile: Vite dev / Node build → nginx)
  docs/
    spec.md             this spec
    adr/                decision records
    ai-usage.md         GenAI section
    ai/prompts/         prompts used per iteration
  .github/workflows/
  .vscode/              settings.json, extensions.json
  docker-compose.yml
  docker-compose.prod.yml
  .pre-commit-config.yaml
  AGENTS.md             rules for any coding agent, plus Code Review Rules for Codex
  CLAUDE.md             imports AGENTS.md
  README.md
```

## 12. AI-assisted workflow

Separate roles, and no agent reviews its own work. See [ADR 0010](adr/0010-ai-workflow-builder-reviewer.md).

| Role | Tool | Works from |
|---|---|---|
| Planning and architecture | Claude (chat) | The brief; drafted this spec and the ADRs with me |
| Builder | Claude Code in VS Code, one fresh session per iteration | `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/` |
| Reviewer (different model family) | Codex code review on every pull request | The PR diff + `## Code Review Rules` in `AGENTS.md` |
| Decision-maker | Me | Approves every decision; reviews tests before implementation |

**Per iteration:**

1. One prompt per iteration, saved to `docs/ai/prompts/NN-name.md` and pasted into a fresh Claude Code session in plan mode.
2. The agent plans before writing anything: the iteration split into small PRs (about 300 changed lines or fewer, not counting `uv.lock` and migrations), each on its own branch `task/<iteration>-<NN>-<name>` from an up-to-date `main`, with every commit listed. I review the plan with Claude in chat before approving it.
3. Tiny commits, one concern each (failing tests, then the implementation that passes them). Every commit waits for my approval and carries a `Co-Authored-By: Claude` trailer, added automatically by `.claude/settings.json`.
4. My corrections follow as separate commits without the trailer, each saying what was wrong.
5. The agent pushes each branch and opens its PR; both wait for my approval. Codex reviews automatically; P0/P1 findings get fixed by me or the builder, never by the reviewer.
6. I merge with a merge commit once CI is green and the review is addressed.

**The headline prompt** ([`docs/ai/prompts/01-scaffold.md`](ai/prompts/01-scaffold.md)) generates the scaffold, not the full implementation. One prompt for everything would skip test-first development and produce more code than can be reviewed carefully; per-iteration prompts keep each output small enough to validate.

**How each point the brief asks about is evidenced:**

| The brief asks for | Evidence |
|---|---|
| The prompt | `docs/ai/prompts/01-scaffold.md`, plus one prompt per iteration |
| Output code | The `Co-Authored-By: Claude` commits from prompt 01, before my corrections, and a representative sample in `docs/ai-usage.md` |
| How suggestions were validated | Tests written first, coverage gate, import-linter, ruff, Codex PR reviews, a manual review checklist |
| Corrections and improvements | A findings table: issue → fix → commit link |
| Edge cases, authentication, validation | Permission-matrix test, transition tests, due-date rules, token refresh and expiry, throttling |
| Performance and idiomatic quality | Query-count tests, `select_related`, `EXPLAIN` on filter queries, a Django/DRF idiom review |

## 13. Iterations

Each iteration ends with tests and CI green, Codex's review addressed, and an ADR for any new decision.

**0. Foundation**
- Planning layer, written before any code: this spec, the ADRs, `AGENTS.md`, `CLAUDE.md`, `.vscode/`, prompt 01
- Prompt 01 generates: uv + pyproject, ruff, pre-commit, import-linter contracts, empty layer packages, Django project with custom `User`, settings from environment, `/api/health/`, backend Dockerfile (dev + prod targets), compose with db, redis, backend, mailpit, pytest + coverage gate, GitHub Actions CI
- Done when: `docker compose up --build` from a clean clone serves `/api/health/`, `uv run pytest` passes, CI is green

**1. Domain and use cases (test first)**
- `Task`, `Status`, transitions, permission rules, errors
- Use cases: create, update, assign, start, complete, reopen, delete; ports as Protocols; in-memory fakes
- Done when: unit tests cover every rule in section 3; import-linter passes

**2. Persistence and read side**
- `Task` model + migration + indexes (`status, due_date`; `assignee`; `owner`); ORM repository; `visible_tasks(user)` selector; FilterSet; admin
- Done when: repository and selector integration tests pass against Postgres

**3. API, auth, docs, throttling**
- JWT with refresh cookie, logout, users endpoints
- Task ViewSet + action endpoints + wiring + exception mapping; pagination; throttles on Redis
- drf-spectacular with the JWT security scheme, Swagger UI
- Done when: API tests cover the permission matrix, filters, pagination, 409/429 paths and query counts; Swagger works end to end

**4. Background jobs and seed data**
- Celery app, Notifier adapter with on_commit, assignment email, Beat reminders, email templates
- `worker` + `beat` services in compose (same image); entrypoint runs `seed_demo`
- Done when: assigning a task in Swagger shows an email in Mailpit; the seed runs twice without duplicates

**5. Frontend foundation**
- Vite + React + TS, ESLint/Prettier, router, Mantine, generated API client
- Auth flow (login, silent refresh, 401 retry, logout), AppShell, responsive layout
- Frontend Dockerfile `dev` target + `frontend` service in compose with the Vite proxy
- Done when: log in/out works, the session survives a page reload, no console warnings

**6. Frontend features**
- Task list with URL-driven filters + pagination; create/edit form; assign; start/complete/reopen; delete with confirmation; notifications; loading/empty/error states
- Vitest + MSW tests; optional Playwright happy path
- Done when: full CRUD works on mobile and desktop widths, no console warnings, tests green

**7a. Production images**
- Backend `prod` target with gunicorn; frontend `prod` target with nginx serving the build and proxying `/api`; `docker-compose.prod.yml`; CI builds both images
- Done when: the prod override runs the full app on http://localhost:8080 with seeded data

**7b. Cloud Run deploy (optional)**
- Backend service, frontend service, a worker pool for the Celery worker, Cloud SQL, Redis; secrets in Secret Manager; deploy from GitHub Actions
- Done when: the demo runs on a public URL with seeded data

**8. Docs and GenAI write-up**
- README: setup, demo credentials, architecture diagram, key decisions linking the ADRs
- `docs/ai-usage.md` completed against the evidence table in section 12
- Final coverage check, tag `v1.0.0`
