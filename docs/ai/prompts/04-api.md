# Prompt 04: API, auth, docs and throttling

- **Iteration:** 3 (API, auth, docs, throttling)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/03-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** fourteen PRs, [#22](https://github.com/aaronjae22/ballast-lane-task/pull/22) ADR 0014 to [#35](https://github.com/aaronjae22/ballast-lane-task/pull/35) action endpoints: the schema and Swagger, JSON only and throttling, the exception handler, the composition root, JWT login, refresh and logout, ordering, reads, filters over HTTP, create, edit and delete, and the action endpoints

## Why the prompt is written this way

- **The workflow is unchanged.** Plan first, small PRs, tiny commits, every commit approved, an ADR before code when a decision binds later work.
- **Iteration 2 left obligations, and the prompt lists them.** ADR 0013 makes the transaction around each write use case a requirement, not a nicety: without it the repository refuses to load. The admin flag, the filters and the error order are already decided; the API has to follow them, not re-decide them.
- **The domain decides; the API translates.** Serializers check the shape of the input only, and every rule comes back as a domain error mapped to one status code (ADR 0012). A serializer that re-checks a rule would give a second answer to the same question.
- **The permission matrix reaches its third level.** The same rows that drive the domain and use-case tests now drive the HTTP test, so a view wired to the wrong use case or the wrong queryset fails.
- **The schema is a contract.** The frontend generates its types from it in iteration 5, so the prompt asks for a schema that validates without warnings, not just a Swagger page that loads.
- **Open decisions come back as questions with a proposed answer.** This iteration has more of them than any before it (notifier, cache, pagination, token lifetimes), so they're named.

## The prompt

```text
You're building iteration 3 (API, auth, docs, throttling) of this repo. Before anything else, read AGENTS.md, CLAUDE.md, docs/spec.md (especially sections 3, 4, 5, 6, 7 and 9) and every file in docs/adr/ (especially 0002, 0003, 0004, 0005, 0006, 0012 and 0013). Iterations 0 to 2 are merged: look at tasks/application/ (the use cases and ports), tasks/infrastructure/, tasks/selectors.py, tasks/api/filters.py, accounts/models.py, config/settings.py and config/urls.py, and the tests in tests/unit/, tests/integration/ and tests/api/.

Goal: the HTTP API from spec section 5, with JWT auth as in ADR 0006, throttling, pagination, the error mapping, and an OpenAPI schema with Swagger UI, all covered by API tests. Every write goes through a use case; every read goes through visible_tasks.

IN SCOPE

1. Auth (spec section 6, ADR 0006): simplejwt with the token_blacklist app.
   - POST /api/auth/token/: username and password; returns the access token in the body and sets the refresh token as an httpOnly, SameSite=Strict cookie scoped to /api/auth/, Secure outside local development. Throttle scope auth.
   - POST /api/auth/token/refresh/: reads the refresh cookie, rotates it (the old one is blacklisted), returns a new access token and sets the new cookie.
   - POST /api/auth/logout/: blacklists the refresh token from the cookie and clears the cookie.
   - Access token lifetime 5 minutes.
2. Users: GET /api/users/ (active users, id and display name, for the assignee picker) and GET /api/users/me/ (the current user).
3. Tasks:
   - Reads: list and detail through visible_tasks(request.user), filtered with TaskFilter (the view passes no clock, so the real one is used), ordered by due_date, created_at or status, paginated. A task outside the user's visibility is 404.
   - Writes: POST /api/tasks/ (optional assignee_id), PATCH /api/tasks/{id}/ (title, description and due date only; a field left out of the body is UNSET, an explicit null due date clears it), DELETE /api/tasks/{id}/, and POST /api/tasks/{id}/assign/, /start/, /complete/ and /reopen/ (ADR 0004). Each calls exactly one use case. No PUT.
   - tasks/api/wiring.py, the composition root: builds each use case with the real adapters and runs it inside transaction.atomic() (ADR 0013; the repository's get() raises without it). Maps the request's user to Actor(id=user.pk, is_admin=user.is_admin) in one place, and nowhere else.
   - Serializers check the shape of the input only (types, required fields). The rules (title length after stripping, past due dates, active assignee, transitions, permissions) stay in the domain and come back as domain errors (ADR 0012).
4. The DRF exception handler, the one place errors become HTTP (AGENTS.md): TaskNotFound -> 404, NotAllowed -> 403, InvalidTransition -> 409, DomainValidationError -> 400 keyed by its field, like DRF's own validation errors. A missing or hidden task is 404, including TaskNotFound raised by the repository's save() when the row is gone. Filter errors are 400.
5. Throttling (spec section 7): anonymous 30/min, authenticated 120/min, auth scope 5/min, stored in the cache; 429 with Retry-After.
6. drf-spectacular (ADR 0005): /api/schema/ and Swagger UI at /api/docs/, with the JWT bearer scheme, so a token pasted into Swagger's Authorize works. Each action endpoint shows its own request body, response and error responses, and the filters show their help text. The schema must validate with no warnings: iteration 5 generates the frontend's types from it.
7. API tests under tests/api/, written first:
   - The permission matrix through HTTP, driven by tests/unit/permission_matrix.py, all five rows including view (detail and list), for every role, with the status codes from spec section 3.
   - Each endpoint's happy path, and the error paths: 400 (shape and domain), 403, 404, 409, 429, and 401 without a token.
   - The auth flow: login sets the cookie with the right attributes and no refresh token in the body; refresh rotates and the old refresh token is refused; logout blacklists and clears the cookie; an expired access token is 401.
   - The transaction boundary: a write that fails after loading (for example an invalid transition) saves nothing; and a test that would fail if a write use case ran outside transaction.atomic().
   - Filters through HTTP (the integration tests already cover their logic, so a few cases each), ordering, pagination.
   - Query counts on list and detail (django_assert_max_num_queries), so adding tasks doesn't add queries.
   - The schema validates with no warnings.
8. EXPLAIN on the filter queries (spec section 9), especially overdue (status not done and due_date before today) against the (status, due_date) index. On a small table Postgres sequential-scans anyway, so say how you make the check meaningful, and where the result is recorded.

OUT OF SCOPE (don't build any of this, not even partially)

- The Celery Notifier adapter, email templates, Beat reminders, seed_demo, worker and beat services (iteration 4)
- Anything in frontend/ (iterations 5 and 6), CORS (one origin, ADR 0006)
- Changes to tasks/domain/ and tasks/application/. If an endpoint can't be built on the use cases as they are, stop and tell me.
- Changes to the import-linter contracts or the coverage settings

CONSTRAINTS

- Follow AGENTS.md and the ADRs. If something here conflicts with them, stop and say so.
- Where the spec and the ADRs don't decide something, don't guess. List it as a question in the plan, with the option you'd pick and why. At least:
  - Which Notifier the wiring uses until iteration 4 brings the Celery adapter, and how that stays a one-line swap.
  - The cache in tests and on this machine: Redis isn't published to the host and may not run locally; throttling needs a cache, and throttle state must not leak between tests.
  - Page size and its query parameter, and the default ordering (pagination needs a stable order; tasks without a due date have to sort somewhere).
  - The refresh token's lifetime, how "Secure outside local development" is decided, and what logout does without a cookie.
  - What /api/users/ returns as the display name, and what /api/users/me/ includes (for example is_admin, which the frontend may need).
  - The response bodies: what create, PATCH and the action endpoints return, and the status codes (201, 200, 204).
  - Whether the browsable API stays on, and so whether django_filters goes into INSTALLED_APPS.
  - factory-boy, still an unused dev dependency: adopt it in these tests or remove it.
  - Which of these answers belong in an ADR (0014) before the code, as in iteration 2.
- No new dependencies beyond what's in pyproject.toml, unless you say why in the plan.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer (not counting migrations and uv.lock), on its own branch named task/03-NN-short-name, created from an up-to-date main. If an ADR is needed, it comes first, docs only.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first: each endpoint group, the exception handler, the auth flow and throttling get a test: commit with the failing tests, then a feat: commit that makes them pass. For each test: commit, show the pytest summary lines and why the tests fail (a missing route, module or attribute, never a typo).
   - Show the public shape: URL routes, view classes and their actions, serializers and their fields, the wiring functions, the exception handler's mapping, and the settings you add. No bodies.
   - List every question and assumption.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Verify, and include the output of each command in your summary. Docker doesn't run on this machine, so the database commands use the local Postgres:
   - cd backend && uv run ruff check . && uv run ruff format --check .
   - cd backend && uv run lint-imports
   - cd backend && DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run python manage.py makemigrations --check --dry-run
   - cd backend && DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run python manage.py spectacular --validate --fail-on-warn --file /dev/null
   - cd backend && uv run pytest tests/unit --cov-fail-under=0 && uv run coverage report --include='tasks/domain/*,tasks/application/*' --fail-under=100
   - cd backend && DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run pytest   (the full suite, with the 80% gate)
   - uv run --project backend pre-commit run --all-files
   - Once the endpoints exist: say how to run the server locally and walk through Swagger end to end (log in, authorize, create, assign, complete, list with a filter), and what that needs on this machine.
4. Finish with a summary: what you created, every deviation from the spec and the ADRs and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

**Plan.** The plan's conventions became ADR 0014 before any code. The plan review changed one decision. The plan cleared the refresh cookie on a failed refresh, but two refreshes can race: the loser would delete the cookie the winner had just set, and log the user out. A failed refresh now answers 401 and leaves the cookie alone.

**Build.**
- Measuring the filter queries with `EXPLAIN` on 100,000 tasks found that the status filter added a `DISTINCT` that removed nothing but sorted whole rows: 17.4 ms instead of 0.43 ms. Fixed with `distinct=False` and a test that no filter adds `DISTINCT` ([5f54f2a](https://github.com/aaronjae22/ballast-lane-task/commit/5f54f2a)); the plans are in [`docs/query-plans.md`](../../query-plans.md).
- Schema tests written before the frontend caught two things its generated types would have inherited: `overdue` typed as a boolean with string choices ([a279627](https://github.com/aaronjae22/ballast-lane-task/commit/a279627)), and a request body named `LoginRequestRequest` ([9a4ea17](https://github.com/aaronjae22/ballast-lane-task/commit/9a4ea17)).
- The list takes at most 3 queries however many tasks there are, and a task's detail at most 2.

**Codex review.**
- #23, P2: the schema and Swagger endpoints weren't throttled, though ADR 0014 says they are. The next PR, #24, turned throttling on for every endpoint but health, with tests that the 31st anonymous request is a 429 ([d09d8b4](https://github.com/aaronjae22/ballast-lane-task/commit/d09d8b4)).
- #26, P2: INFO messages from `tasks.*` were dropped, because Django configures only its own logger; the tests hid it because `caplog` lowers the level. Failing test first ([b456e5c](https://github.com/aaronjae22/ballast-lane-task/commit/b456e5c)), then a logging config ([b4d84bb](https://github.com/aaronjae22/ballast-lane-task/commit/b4d84bb)).
