# AGENTS.md

Instructions for any coding agent working in this repo (Claude Code, Codex, Copilot, Cursor). People should start with `README.md`.

## What this is

Team Task Board: a task management REST API (Django + DRF) with a React + TypeScript frontend. The specification is `docs/spec.md`; the reasons behind the main decisions are in `docs/adr/`. Read both before changing anything. If a request conflicts with them, stop and say so instead of working around it.

## Repo layout

- `backend/`: Django project managed by uv (`config/`, `accounts/`, `tasks/`, `tests/`)
- `frontend/`: React + TypeScript app built with Vite
- `docs/`: spec, ADRs, AI usage write-up, saved prompts
- `docker-compose.yml`, `docker-compose.prod.yml`: local stack and production-image override

## Commands

Created in iteration 0. Whoever adds or changes a command updates this list in the same commit.

- Whole stack: `docker compose up --build`
- Backend (run from `backend/`):
  - Install: `uv sync`
  - Tests: `uv run pytest`
  - Lint and format: `uv run ruff check .` and `uv run ruff format .`
  - Architecture contracts: `uv run lint-imports`
  - Django: `uv run python manage.py <command>`
- Frontend (run from `frontend/`, from iteration 5): `npm ci`, `npm run dev`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run gen:api`
- All pre-commit hooks: `uv run --project backend pre-commit run --all-files` (from the repo root)

## Backend architecture rules

- **Dependency rule.** `tasks/domain/` imports only the standard library. `tasks/application/` imports only `tasks/domain/`. `tasks/infrastructure/` and `tasks/api/` may import inward. import-linter enforces this; never weaken a contract to make it pass.
- **Writes go through use cases** in `tasks/application/`. Views, serializers and models never change task state directly.
- **Reads go through `tasks/selectors.py`**, which returns QuerySets. Every read applies `visible_tasks(user)`.
- **Business rules** (permissions, status transitions, due-date validation) live in `tasks/domain/` and nowhere else.
- **Errors map to HTTP in one place**, the DRF exception handler: `NotAllowed` → 403, `TaskNotFound` or not visible → 404, `InvalidTransition` → 409, `DomainValidationError` → 400.
- **Side effects** (email, Celery) go through the `Notifier` port. The Celery adapter enqueues inside `transaction.on_commit`.
- **Wiring.** Use cases receive their dependencies as constructor arguments; real adapters are wired in `tasks/api/wiring.py`.
- Django's own files (`models.py`, `admin.py`, `apps.py`, `migrations/`) stay where Django expects them.

## Frontend rules

- Server state only through TanStack Query hooks in `features/*/hooks/`; components never call `fetch` directly.
- API types in `src/api/` are generated. Never edit them by hand; run `npm run gen:api`.
- Mantine for all UI; no other component library or CSS framework.
- The access token lives in memory only. Never write tokens to localStorage or sessionStorage.
- Filters live in URL query parameters.
- No warnings or errors in the browser console (React StrictMode is on).

## Testing rules

- **Test first** for domain rules and use cases: write the failing test and commit it (`test: ...`), then implement (`feat: ...`).
- Unit tests (`tests/unit/`) never touch the database; use the in-memory fakes.
- Any permission change needs a matching row in the permission-matrix test.
- List and detail endpoints have query-count assertions; keep them passing.
- The coverage gate is 80%. Don't lower it, and don't add `pragma: no cover` to reach it.

## Code style

- Python: ruff handles lint and format. Type hints on public functions. Dataclasses for domain objects.
- TypeScript: strict mode, no `any`, ESLint + Prettier.
- Use the spec's domain language: owner, assignee, due date, overdue, start, complete, reopen.

## Git

- Commit at each checkpoint (for example: failing tests written, then implementation passing). Conventional Commits, one concern per commit. Every `git commit` waits for my approval.
- Every commit an agent makes ends with a `Co-Authored-By:` trailer naming the agent. Claude Code adds it automatically through `.claude/settings.json`; other agents add it themselves.
- Work on the current iteration branch (`iter/NN-name`). Never commit to `main`, push, merge, or rewrite history (no amend, rebase, reset or force push). Corrections are new commits.
- Never skip hooks (`--no-verify`).
- Don't add a dependency without saying why in your summary.

## Scope

- Do only what the current iteration's prompt asks. If you notice something outside it, list it in your summary instead of doing it.
- Don't edit `docs/spec.md` or `docs/adr/` unless asked. If you make a decision the spec doesn't cover, propose an ADR in your summary.
- When a requirement is unclear, ask instead of guessing.
- End every task with a summary: what changed, the commands you ran and their results, assumptions, and anything you skipped.

## Code Review Rules

Used by Codex code review on pull requests. Flag these as P1 unless marked P0. Don't flag formatting; ruff and Prettier handle it.

### Security

- (P0) A task read that skips `visible_tasks(user)`. A task outside a user's visibility must return 404.
- (P0) Tokens written to localStorage or sessionStorage, or the refresh token exposed to JavaScript.
- An endpoint without authentication or throttling, unless the spec says it's public (`/api/health/`, login, refresh).
- Permission checks that differ from the matrix in `docs/spec.md` section 3.
- Secrets or credentials committed to the repo, other than the clearly marked local defaults.

### Architecture

- `tasks/domain/` or `tasks/application/` importing Django, DRF, Celery, `tasks/infrastructure/` or `tasks/api/`.
- A view, serializer or model method that changes task state without going through a use case.
- Business rules implemented outside `tasks/domain/`.

### Data and side effects

- A Celery task enqueued outside `transaction.on_commit`.
- List or detail queries that can cause N+1 queries (missing `select_related`), or a removed query-count assertion.
- A migration that isn't reversible, or that changes existing data without a data migration.

### Tests

- New or changed behavior without tests.
- A lowered coverage threshold, or tests skipped or marked xfail without a stated reason.
- Unit tests that hit the database.

### Frontend

- `fetch` calls inside components instead of query hooks.
- Hand edits to the generated API types.
- Code that causes browser console warnings (missing list keys, effects without cleanup, uncontrolled-to-controlled inputs).
