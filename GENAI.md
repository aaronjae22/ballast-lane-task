# GenAI: how AI was used to build this project

This file answers the brief's "Generative AI tools" section. The workflow is also described in [`docs/spec.md`](docs/spec.md) section 12 and [ADR 0010](docs/adr/0010-ai-workflow-builder-reviewer.md).

| The brief asks for | Where |
|---|---|
| The prompt I would use to generate the scaffold | [The prompt](#the-prompt) |
| The output code, or a representative sample | [The output](#the-output) |
| How I validated the AI's suggestions | [How I validated the AI's suggestions](#how-i-validated-the-ais-suggestions) and [Test-driven development](#test-driven-development) |
| How I corrected or improved the output | [What I corrected or improved](#what-i-corrected-or-improved) |
| Edge cases, authentication and validation | [Edge cases, authentication and validation](#edge-cases-authentication-and-validation) |
| Performance and idiomatic quality | [Performance and idiomatic quality](#performance-and-idiomatic-quality) |
## Tools and roles

| Role | Tool | What it did |
|---|---|---|
| Planning and architecture | Claude (chat) | Drafted the spec, the ADRs and every prompt with me; reviewed each plan before I approved it |
| Builder | Claude Code in VS Code | One fresh session per iteration, in plan mode first; wrote the tests and the code, opened the PRs |
| Reviewer | Codex code review on GitHub pull requests | A different model family, reviewing every PR against `## Code Review Rules` in `AGENTS.md` |
| Decision-maker | Me | Answered the open questions, approved each plan, commit and PR, and merged once CI and the review were addressed |

No agent reviewed its own work: Claude Code built, Codex reviewed, and the plan review happened in a separate chat that never wrote code.

## The prompt

The headline prompt is [`docs/ai/prompts/01-scaffold.md`](docs/ai/prompts/01-scaffold.md), for Claude Code in plan mode. It generates the scaffold, not the whole app: tooling, layer packages, the Django project, the health endpoint, Docker, compose and CI. One prompt for everything would have skipped test-first development and produced more code than I could review properly.

<details>
<summary>The full prompt</summary>

```text
You're scaffolding iteration 0 (Foundation) of this repo. Before anything else, read AGENTS.md, CLAUDE.md, docs/spec.md (especially sections 4, 9, 10, 11 and 13) and every file in docs/adr/.

Goal: a working foundation that every later iteration builds on, wired end to end but with no business features.

IN SCOPE

1. backend/ is a uv project: pyproject.toml with project metadata, a dev dependency group, and tool config for ruff, pytest, coverage and import-linter; a committed uv.lock; Python 3.13.

2. Django 5.2 LTS project in backend/:
   - config/ package: settings, urls, wsgi, asgi, and a Celery app module (app defined, no tasks yet).
   - accounts app: custom User model extending AbstractUser, AUTH_USER_MODEL set, registered in the admin, initial migration.
   - tasks app, empty, with the layer packages from spec section 4: domain/, application/, infrastructure/, api/, plus selectors.py. Each package's __init__.py gets a one-line docstring saying what belongs there and what it may import.

3. Settings from environment variables with safe local defaults, so the app starts with no .env file. Provide .env.example at the repo root. DEBUG is off unless set. SECRET_KEY comes from the environment; the local default is clearly marked insecure and refused when DEBUG is off. DATABASE_URL for Postgres, REDIS_URL for the cache, SMTP settings pointing at Mailpit for local email.

4. DRF configured with simplejwt's JWTAuthentication as the default authentication class, IsAuthenticated as the default permission, and drf-spectacular as the schema class. One endpoint: GET /api/health/ (no auth), which checks the database connection and returns {"status": "ok"}, or 503 if the database is down.

5. Dependencies. Runtime: django, djangorestframework, djangorestframework-simplejwt, drf-spectacular, django-filter, celery, redis, psycopg (binary extra), gunicorn. Dev: pytest, pytest-django, pytest-cov, factory-boy, ruff, import-linter, pre-commit. Resolve them with uv and confirm each supports Python 3.13 and Django 5.2. Report the versions you resolved and anything that didn't fit.

6. ruff: select E, F, W, I, B, UP, DJ, SIM, RUF on top of the defaults, line length 100. Explain any rule you add or ignore.

7. import-linter contracts in pyproject.toml, exactly as in spec section 4: tasks.domain independent of django, rest_framework and celery; tasks.application may import only tasks.domain; tasks.domain and tasks.application never import tasks.infrastructure or tasks.api. They must pass against the empty packages.

8. pytest: settings module configured, test paths backend/tests/unit, backend/tests/integration and backend/tests/api, coverage of the backend packages with fail_under = 80. Tests for: /api/health/ returns 200 with the database up; /api/health/ returns 503 when the database check fails; AUTH_USER_MODEL is the custom user. Add a separate test settings module only if you need one, and say why.

9. backend/Dockerfile, multi-stage, as in spec section 10: base (python:3.13-slim plus uv copied from its official image), a deps layer cached on uv.lock, a dev target (dev dependencies, runserver), and a prod target (no dev dependencies, non-root user, collectstatic, gunicorn). An entrypoint script that runs migrate and then execs the given command (the seed step comes in iteration 4). backend/.dockerignore.

10. docker-compose.yml at the repo root: db (postgres:17, healthcheck, named volume, port 5432 published for host-side tests), redis (healthcheck), backend (dev target, source mounted, depends_on db and redis being healthy, port 8000), mailpit (ports 1025 and 8025). No worker, beat or frontend services yet; they come in iterations 4 and 5.

11. .pre-commit-config.yaml: local hooks that run ruff check --fix, ruff format and lint-imports through uv against backend/; uv's lock check; hadolint for Dockerfiles; standard hygiene hooks (end-of-file-fixer, trailing-whitespace, check-yaml, check-toml, check-added-large-files). No frontend hooks yet.

12. .github/workflows/ci.yml on push and pull_request. Job "backend": set up uv, Postgres 17 and Redis service containers, ruff check, ruff format --check, lint-imports, pytest with coverage. Job "docker": build the backend prod target.

13. Update the Commands section of AGENTS.md so it matches exactly what you created.

OUT OF SCOPE (don't build any of this, not even partially)

- The Task model, domain entities, use cases, serializers, and any endpoint other than /api/health/
- JWT login, refresh and logout views; throttle rates; Celery tasks; seed_demo
- Anything in frontend/

CONSTRAINTS

- Follow AGENTS.md: architecture rules, git rules, scope rules.
- Prefer Django and DRF defaults. Don't add configuration you can't explain, and say where you deviated from a default.
- No secrets in the repo.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer (not counting uv.lock and migrations), on its own branch named task/00-NN-short-name, created from an up-to-date main.
   - Order the PRs so CI and pre-commit arrive early, and every later PR gets checked.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Also list the dependency versions you resolved and every question or assumption.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2–5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2–3 line note on what the commit does; every commit waits for my approval.
   - When a PR's commits are done, run the checks below that apply to it, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Verify, and include the output of each command in your summary:
   - cd backend && uv run ruff check . && uv run ruff format --check .
   - cd backend && uv run lint-imports
   - docker compose up --build -d, then curl -s localhost:8000/api/health/
   - cd backend && uv run pytest   (against the compose database)
   - docker build --target prod backend/
   - uv run --project backend pre-commit run --all-files
4. Finish with a summary: what you created, every deviation from the spec and why, anything you weren't sure about, and anything you noticed but left out of scope.
```

</details>

Why it's written this way:

- **It points to the spec instead of restating it**, so there's one source of truth and the prompt stays short enough to review.
- **Scope and non-goals are explicit.** The most common failure of a scaffold prompt is the agent helpfully building features nobody asked for yet.
- **Exact choices where they matter** (versions, contracts, Docker stages), and freedom where they don't.
- **"Done" is a list of commands**, so success is something to verify, not something the agent claims.
- **Plan and questions first.** Nothing is written until the plan, the resolved versions and the assumptions have been reviewed.
- **Versions are checked, not recalled.** The agent resolves them with uv instead of trusting its memory.
- **Small PRs, tiny commits.** The plan splits the work into PRs of about 300 changed lines, each made of commits that do one thing and explain why. Every commit waits for my approval, so each one has been read by a person before it exists.

### How my prompting changed

The first run of this prompt taught me more than the code did, and the later prompts are built on it:
- **The plan found gaps in my own prompt.** It asked for `DATABASE_URL` but named no parser, and it chose a host port that clashed with my local Postgres. Every prompt since asks for each open decision to come back as a question with a proposed answer, so the gaps surface before any code.
- **Small output is reviewable output.** The first run produced one commit of about 1,400 lines; I set it aside and restarted with the workflow written into the prompt: PRs of about 300 lines, one concern per commit, failing tests first, and every commit approved.
- **Standing context lives in files, not prompts.** `AGENTS.md`, `CLAUDE.md`, the spec and the ADRs hold the rules, so each prompt only says what's new in its iteration, and a fresh session per iteration starts from the same ground truth.
- **Decisions are written down before the next prompt.** When a plan or a review settles something, it becomes an ADR first (18 of them), so the next session can't quietly undo it.
- **The reviewer gets rules, not vibes.** Codex reviews against `## Code Review Rules` in `AGENTS.md`, with P0/P1 severities. When a rule would misfire on a deliberate choice, the ADR states the rule's scope (rows 18 and 23 below).

Every iteration has its own prompt, saved before the run:

| Iteration | Prompt |
|---|---|
| 0. Foundation | [`01-scaffold.md`](docs/ai/prompts/01-scaffold.md) |
| 1. Domain and use cases | [`02-domain.md`](docs/ai/prompts/02-domain.md) |
| 2. Persistence and read side | [`03-persistence.md`](docs/ai/prompts/03-persistence.md) |
| 3. API, auth, docs, throttling | [`04-api.md`](docs/ai/prompts/04-api.md) |
| 4. Background jobs and seed data | [`05-background-jobs.md`](docs/ai/prompts/05-background-jobs.md) |
| 5. Frontend foundation | [`06-frontend-foundation.md`](docs/ai/prompts/06-frontend-foundation.md) |
| 6. Frontend features | [`07-frontend-features.md`](docs/ai/prompts/07-frontend-features.md) |

Each prompt has the same shape: the goal and the spec sections it covers, the open questions the agent must answer in its plan, how to split the work into PRs, and what "done" means. The `Result` and `Review notes` at the end of each one record what happened.

## The output

73 pull requests and 288 commits on `main` before this write-up. 279 of the commits carry the agent's `Co-Authored-By: Claude` trailer. The other 9 are mine, and they're all documentation: the spec, the ADR set and the prompts, as are the commits of the final docs PRs.

That ratio needs explaining, because the spec planned for my corrections to land as separate commits without the trailer. In practice most corrections happened earlier: in the plan review, before any code existed, or as instructions to the builder, which then made the fix in its own commit. The fixes are still separate commits that say what was wrong; the table below lists them.

To list commits with their co-authors:

```bash
git log --format='%h  %<(48,trunc)%s  %(trailers:key=Co-Authored-By,valueonly,separator=%x2C )'
```

A representative sample. The status rules are one table that mirrors spec section 3 ([db27f7f][db27f7f], `backend/tasks/domain/task.py`):

```python
_TRANSITIONS: dict[str, tuple[frozenset[Status], Status]] = {
    "start": (frozenset({Status.TO_DO}), Status.IN_PROGRESS),
    "complete": (frozenset({Status.TO_DO, Status.IN_PROGRESS}), Status.DONE),
    "reopen": (frozenset({Status.DONE}), Status.TO_DO),
}
```

And a use case, which only orchestrates: access check, domain method, save, then the email the domain rule asks for ([70242c1][70242c1], `backend/tasks/application/assign_task.py`):

```python
def execute(self, actor: Actor, task_id: int, assignee_id: int | None) -> Task:
    task = get_task_for(self._tasks, actor, task_id, Action.ASSIGN)
    previous_assignee_id = task.assignee_id
    task.assign(
        assignee_id,
        assignee_is_active=assignee_id is not None and self._users.is_active_user(assignee_id),
        now=self._clock.now(),
    )
    self._tasks.save(task)
    # The None check only narrows the type for task_assigned; the domain rule decides.
    if assignee_id is not None and assignment_email_due(
        previous_assignee_id=previous_assignee_id,
        new_assignee_id=assignee_id,
        changed_by_id=actor.id,
    ):
        self._notifier.task_assigned(task_id=task_id, assignee_id=assignee_id)
    return task
```

The repository, the clock and the notifier are Protocols, so the use case runs against in-memory fakes in unit tests and against the ORM and Celery in production.

## How I validated the AI's suggestions

Each check sits at a different point, so a mistake one misses has another chance to be caught.

1. **Plan before code.** Every run started in plan mode: the PRs, every commit, and answers to the prompt's open questions. I reviewed each plan with Claude in chat, usually over two rounds, before approving it. Several of the most important corrections below were made here, when they cost nothing.
2. **Tests first.** Each rule landed as a failing-test commit, then the implementation that passes it, so every test was seen to fail for the right reason.
3. **Gates in CI**, on every PR:
   - `backend`: ruff (lint and format), import-linter contracts that keep the domain free of Django ([ADR 0011](docs/adr/0011-import-linter-contracts.md)), and pytest with an 80% coverage gate. Iteration 1 also checked the domain and application layers for 100% line and branch coverage, as a failing command, not a number to read.
   - `frontend`: ESLint with type information, Prettier, the TypeScript check, Vitest, and the production build. A test fails if it logs a console warning or error it didn't declare.
   - `api-contract`: regenerates the OpenAPI schema and the TypeScript types, and fails if the committed ones are stale.
   - `e2e`: Playwright walks the happy path in Chromium; any console warning or page error fails it ([ADR 0018](docs/adr/0018-frontend-task-screens.md)).
   - `docker`: builds the prod image, starts the compose stack and checks it end to end: health, every migration applied, a second seed creating nothing, an assignment email and the reminder digests reaching Mailpit, the frontend proxy, and login and refresh through it.
4. **Codex review** on every PR, with the P0/P1 rules in `AGENTS.md`. Its findings were fixed by me or the builder, never by the reviewer.
5. **My own checks**, beyond the green ticks:
   - I read each PR's diff. Reading the config by hand found a bug no test could: `.env.example` set `DJANGO_DEBUG=false`, which would have broken compose for anyone who copied it.
   - I reran the unit tests of merged PRs myself with warnings as errors (`-W error`), which reproduced a pytest deprecation the agent had fixed.
   - Mutation checks: I broke the code on purpose to see the right test fail. Giving `UpdateTask` the wrong permission row failed exactly one cell of the use-case matrix, the one it should.
   - Manual browser checks, written into prompts 06 and 07, once there were pages to use.
   - A run of `docker compose up --build` from a fresh clone, as a reviewer would do it.

## Test-driven development

Every prompt asks for the tests first: a commit with failing tests, then the commit that makes them pass, each approved before it exists.

- **On `main`:** 117 `test:` commits and 93 `feat:` commits. 82 of the 93 features come straight after their failing tests.
- **The other 11 are wiring:** the Django skeleton and settings, app registration, the Celery app, the ports (Protocols, exercised through the fakes' own tests), and the compose and Vite proxy configuration, which the CI smoke test checks end to end. One of them is where test-after went wrong: the settings tests proved the settings import, not that each variable reaches its setting, and Codex caught it (row 5 below).
- **Failing for the right reason.** Once a module existed, its next failing-test commit had to fail on the missing behaviour, not on an import error, so the red step proved something.
- **Four levels of tests.** Unit tests for the domain and the use cases run on in-memory fakes, with no database. Integration tests run on Postgres: the repository, the selectors, the query plans, Celery. API tests go through HTTP. The frontend has Vitest with MSW, and Playwright in a real browser.
- **At submission:** 681 backend tests at 99.81% coverage (the gate is 80%), 352 Vitest tests and 4 Playwright tests.
- **One honest limit.** CI runs on each PR's last commit, so it doesn't prove every failing-test commit was red. The builder ran the tests at each one and reported the failure before writing the code; the mutation check above shows the tests do fail when the code is wrong.

## What I corrected or improved

| # | Iteration | What the AI produced | Problem | Fix | Found by | Commit |
|---|---|---|---|---|---|---|
| 1 | 0 | The whole scaffold in one commit of about 1,400 lines | Too much to review properly | Restarted with small PRs and one concern per commit (prompt 01, "How to work") | Me | Prompt 01 [review notes](docs/ai/prompts/01-scaffold.md#review-notes) |
| 2 | 0 | `.env.example` with `DJANGO_DEBUG=false` | Copying it to `.env` breaks compose: the settings refuse the built-in secret key with DEBUG off | `DJANGO_DEBUG=true` in the example | Me, reading the config | Prompt 01 review notes |
| 3 | 0 | A CI action pinned to `setup-uv@v10` | The tag no longer resolves, so CI couldn't start | Pinned to a commit SHA, so a retagged release can't change CI | CI | [246d447][246d447] |
| 4 | 0 | `force-exclude` in `pyproject.toml` | From the repo root, ruff ignores it, so the pre-commit hook rewrote the first migration | `--force-exclude` on the hooks | The agent, on the migration commit | [34eb5be][34eb5be] |
| 5 | 0 | Settings tests | They proved the settings import, not that each environment variable reaches the setting it configures | Tests that load the settings under controlled variables and check each value | Codex (P1, [#4](https://github.com/aaronjae22/ballast-lane-task/pull/4)) | [da1b977][da1b977] |
| 6 | 0 | `entrypoint.sh` | Nothing ran it, so nothing proved migrations run before the server starts | Tests that run the real script | Codex (P1, [#5](https://github.com/aaronjae22/ballast-lane-task/pull/5)) | [fb1adfc][fb1adfc] |
| 7 | 0 | Compose without a backend healthcheck | `--wait` counted the backend ready while it was still migrating, and the smoke test failed | A healthcheck on `/api/health/` | CI | [ba431c6][ba431c6] |
| 8 | 1 | Coverage of the domain at 100% as a target | A number to read, not a check | A failing check through command-line flags for the iteration's runs | Plan review | Prompt 02 [review notes](docs/ai/prompts/02-domain.md#review-notes) |
| 9 | 1 | `parametrize` given a `zip` | Deprecated: fails in pytest 10 | A list | The agent; I reproduced it | [ae6659a][ae6659a] |
| 10 | 2 | The Django admin's default queryset | A task read that skips `visible_tasks`, a P0 in `AGENTS.md`. Nothing leaked (only admins reach it), but it was a second definition | The admin reads through `visible_tasks`, at 5 queries a page | Codex (P0, [#16](https://github.com/aaronjae22/ballast-lane-task/pull/16)) | [dff5be2][dff5be2] |
| 11 | 2 | The assignee filter | A 5,000-digit id passed the digit check, then `int()` raised past Python's 4,300-digit limit: a 500 | At most 19 digits before `int()`, bounded by the column, so it's a 400 | Codex (P2, [#21](https://github.com/aaronjae22/ballast-lane-task/pull/21)) | [313dd15][313dd15] |
| 12 | 3 | Plan: a failed refresh clears the cookie | A losing parallel refresh would delete the cookie the winner had just set, logging the user out | A failed refresh leaves the cookie alone ([ADR 0014](docs/adr/0014-api-conventions.md)) | Plan review | [7a0579a][7a0579a] |
| 13 | 3 | The schema and Swagger endpoints | Public and unthrottled, though ADR 0014 says they're throttled as anonymous | Throttling on for every endpoint but health, with tests that the 31st anonymous request is a 429 | Codex (P2, [#23](https://github.com/aaronjae22/ballast-lane-task/pull/23)) | [d09d8b4][d09d8b4] |
| 14 | 3 | Log messages from `tasks.*` | Django configures only its own logger, so INFO messages were dropped; the tests hid it because `caplog` lowers the level | A logging config that sends them to stderr | Codex (P2, [#26](https://github.com/aaronjae22/ballast-lane-task/pull/26)) | [b4d84bb][b4d84bb] |
| 15 | 3 | The status filter, `distinct=True` by default | A `DISTINCT` that removes nothing, but sorts whole rows: 17.4 ms instead of 0.43 ms at 100,000 tasks | `distinct=False`, and a test that no filter adds `DISTINCT` | `EXPLAIN` measurement | [5f54f2a][5f54f2a] |
| 16 | 3 | The login body in the schema | Came out as `LoginRequestRequest`, which the generated types would inherit | Renamed the serializer | A schema test, written first | [9a4ea17][9a4ea17] |
| 17 | 4 | Plan: a hard-coded password for the seeded superuser | Any reachable deployment would have a known admin password | `SEED_DEMO_PASSWORD`, with the default for local use only ([ADR 0015](docs/adr/0015-background-jobs-and-demo-data.md)) | Plan review | [30e11a1][30e11a1] |
| 18 | 4 | Plan: the reminder job finds its recipients across all users | Reads like the P0 "every task read applies `visible_tasks`" | The rule's scope written into ADR 0015: a system job says so in its docstring, and each digest still reads through `visible_tasks` | Plan review | [30e11a1][30e11a1] |
| 19 | 4 | `monkeypatch` on Celery's eager flag | Celery doesn't store the default, so teardown tried to delete a missing attribute | A fixture that saves and restores it | The agent | [62f50d6][62f50d6] |
| 20 | 5 | Refresh without a cookie answering 401 | A red 401 in the console on every page load of a logged-out user | 204 when there's no cookie ([ADR 0016](docs/adr/0016-frontend-foundation.md)) | Plan review | [cf5ac24][cf5ac24] |
| 21 | 5 | `ordering` sent through openapi-fetch | It repeats array parameters, so all but the last ordering field were lost | A serializer for the parameters the schema declares with `explode: false` | Codex (P2, [#45](https://github.com/aaronjae22/ballast-lane-task/pull/45)) | [0abd8d8][0abd8d8] |
| 22 | 5 | Login and refresh during logout | A late answer could sign the user back in after logout | A login that answers after logout is discarded; no refresh starts during logout ([ADR 0017](docs/adr/0017-session-concurrency-rules.md)) | Codex (P2, [#46](https://github.com/aaronjae22/ballast-lane-task/pull/46), [#48](https://github.com/aaronjae22/ballast-lane-task/pull/48)) | [0aa55a2][0aa55a2], [4a58f8b][4a58f8b] |
| 23 | 6 | Plan: the frontend shows which actions a user can take | Copies of the domain rules outside the domain, which Codex would flag | A stated scope: display hints only, the API decides, and a frontend permissions test row for every permission change ([ADR 0018](docs/adr/0018-frontend-task-screens.md)) | Plan review | [cc95933][cc95933], [e5eacca][e5eacca] |
| 24 | 6 | The debounced search box | A search still waiting to be written could undo Back or Clear filters | The write is dropped once the URL has moved past it | Codex (P2, [#62](https://github.com/aaronjae22/ballast-lane-task/pull/62)) | [747fdd8][747fdd8] |
| 25 | 6 | The edit mutation's cache updates | Untested: the tests checked the request and the page, not what the cache held afterwards | Tests that inspect the query cache after a save | Codex (P1, [#67](https://github.com/aaronjae22/ballast-lane-task/pull/67)) | [be013ed][be013ed] |
| 26 | 6 | The Assign dialog | Closing it while saving lost the pending state, so a reopened dialog could assign twice | The task's actions own the save, and wait for it | Codex (P2, [#69](https://github.com/aaronjae22/ballast-lane-task/pull/69)) | [ab97e9e][ab97e9e] |
| 27 | 6 | Codex's review of the e2e login | It said the password field can't be found by its role and label. A false positive: Playwright gives a password input the `textbox` role, and the CI job had logged in through that locator | No change; I replied with the evidence | Me, reviewing Codex ([#71](https://github.com/aaronjae22/ballast-lane-task/pull/71)) | None |

Codex left 13 findings across the 73 PRs: 1 P0, 4 P1 and 8 P2, and none on iteration 1's five. 12 were valid and fixed: 9 with a failing test first, and 3 that were themselves missing tests. One was a false positive, which I declined with the evidence instead of changing working code to satisfy the reviewer (row 27).

## Edge cases, authentication and validation

Each was specified before the code, in the spec or an ADR, and then tested.

- **Permissions.** One permission matrix (`backend/tests/unit/permission_matrix.py`) drives the tests at every level: the domain rules, every use case, the HTTP endpoints (`tests/api/test_permission_matrix.py`) and the `visible_tasks` selector. The frontend has its own mirror, `frontend/src/features/tasks/permissions.test.ts`. A test checks that the matrix covers every action, so a new one can't be left out.
- **Status transitions.** Only the moves in the table above are allowed; every other one is a 409. An outsider gets 404 even where the status would give 409, so a task's existence doesn't leak.
- **Due dates.** "Can't be in the past" and "overdue" use the local date in `TIME_ZONE`, not UTC. The tests use a clock where today and `now.date()` differ, as in Managua's evening, so a use case that reads the wrong one fails.
- **Authentication** ([ADR 0006](docs/adr/0006-jwt-refresh-cookie-same-origin.md), [0014](docs/adr/0014-api-conventions.md), [0017](docs/adr/0017-session-concurrency-rules.md)). The access token lasts 5 minutes and lives in memory only. The refresh token lasts a day, sits in an httpOnly, SameSite=Strict cookie scoped to `/api/auth/`, and is rotated on each use with the old one blacklisted. Logout blacklists it. The tests cover expiry, reuse of a rotated token, a failed refresh, and the races between login, refresh and logout.
- **Throttling.** 30 requests a minute anonymous, 120 a minute signed in, and 5 a minute on login. The health check isn't throttled. The 429 paths have tests.
- **Validation.** The shape of a request is checked before access: unknown fields and invalid filter values are a 400, never ignored. Rules live in the domain, so the API maps domain errors to HTTP in one exception handler.

## Performance and idiomatic quality

- **Query counts.** The task list takes at most 3 queries however many tasks there are, and a task's detail at most 2 (`tests/api/test_task_reads.py`). `visible_tasks` joins the owner and the assignee once, so there's no N+1.
- **Indexes.** `(status, due_date)` for the status and overdue filters, plus the foreign-key indexes on `owner` and `assignee`.
- **`EXPLAIN` on realistic data.** [`docs/query-plans.md`](docs/query-plans.md) records the plans of the list's filters on 100,000 tasks. The status and overdue filters use the index, a non-admin's list is a cheap `BitmapOr` of the two foreign-key indexes, and the measurement found the `DISTINCT` fix above. It also records what isn't indexed yet, and why. A regression test (`tests/integration/test_query_plans.py`) fails if a change stops these filters from using the index.
- **Writes.** A use case loads its task with `select_for_update` inside the request's transaction, and the assignment email is queued with `on_commit`, so a rolled-back write sends nothing and a broker outage doesn't turn a saved write into a 500.

**Idiomatic quality.** What I checked, and where the code departs from the usual Django way on purpose:
- **Linters as the first reviewer.** ruff runs pyflakes, bugbear, pyupgrade, flake8-django, simplify and its own rules on every commit; the frontend has ESLint with type information and strict TypeScript.
- **Plain Django and DRF where they're the right tool.** The list is a `GenericViewSet` with the list mixin, a django-filter `FilterSet`, a pagination class and throttles from settings. Status changes are `@action` routes. `is_overdue` is annotated in the database, not computed per row in Python. Emails are queued with `transaction.on_commit`.
- **Deliberate departures, each with an ADR.** Writes don't use `ModelSerializer.save()`: a serializer checks the request's shape, and a use case applies the rules, so the rules live in one place and are tested without a database ([ADR 0002](docs/adr/0002-architecture-strict-writes-plain-reads.md)). The cost is a second representation of a task, a dataclass mapped to the model by an 80-line repository. For an app this size a `ModelViewSet` with permission classes would be shorter; I chose the layers because the rules are then tested by unit tests that need no database, and because the brief grades Clean Architecture.
- **The frontend.** Server state lives in TanStack Query, forms use React Hook Form with Zod, filters live in the URL through React Router, and the API types are generated from the OpenAPI schema for openapi-fetch, so no API type is written by hand. Tests mock the network with MSW, not the modules.

## What I'd do differently

- **Record Codex's findings as they arrive.** I logged the plan reviews as they happened, but Codex's findings only in the PR threads, and had to collect them from there for the table above.
- **A type checker in CI.** Nothing checks that the fakes and the adapters match the Protocols they implement; the tests only catch it where they happen to exercise a mismatch.
- **The 100% domain coverage check in CI.** It ran during iteration 1 but never became a CI job, so only the global 80% gate protects it now.
- **Docker working locally from day one.** For the first iterations only CI ran the compose stack, so the startup race in row 7 was found there instead of on my machine.

[db27f7f]: https://github.com/aaronjae22/ballast-lane-task/commit/db27f7f
[70242c1]: https://github.com/aaronjae22/ballast-lane-task/commit/70242c1
[246d447]: https://github.com/aaronjae22/ballast-lane-task/commit/246d447
[34eb5be]: https://github.com/aaronjae22/ballast-lane-task/commit/34eb5be
[da1b977]: https://github.com/aaronjae22/ballast-lane-task/commit/da1b977
[fb1adfc]: https://github.com/aaronjae22/ballast-lane-task/commit/fb1adfc
[ba431c6]: https://github.com/aaronjae22/ballast-lane-task/commit/ba431c6
[ae6659a]: https://github.com/aaronjae22/ballast-lane-task/commit/ae6659a
[dff5be2]: https://github.com/aaronjae22/ballast-lane-task/commit/dff5be2
[313dd15]: https://github.com/aaronjae22/ballast-lane-task/commit/313dd15
[7a0579a]: https://github.com/aaronjae22/ballast-lane-task/commit/7a0579a
[5f54f2a]: https://github.com/aaronjae22/ballast-lane-task/commit/5f54f2a
[9a4ea17]: https://github.com/aaronjae22/ballast-lane-task/commit/9a4ea17
[30e11a1]: https://github.com/aaronjae22/ballast-lane-task/commit/30e11a1
[62f50d6]: https://github.com/aaronjae22/ballast-lane-task/commit/62f50d6
[cf5ac24]: https://github.com/aaronjae22/ballast-lane-task/commit/cf5ac24
[0abd8d8]: https://github.com/aaronjae22/ballast-lane-task/commit/0abd8d8
[0aa55a2]: https://github.com/aaronjae22/ballast-lane-task/commit/0aa55a2
[4a58f8b]: https://github.com/aaronjae22/ballast-lane-task/commit/4a58f8b
[cc95933]: https://github.com/aaronjae22/ballast-lane-task/commit/cc95933
[e5eacca]: https://github.com/aaronjae22/ballast-lane-task/commit/e5eacca
[747fdd8]: https://github.com/aaronjae22/ballast-lane-task/commit/747fdd8
[ab97e9e]: https://github.com/aaronjae22/ballast-lane-task/commit/ab97e9e
[d09d8b4]: https://github.com/aaronjae22/ballast-lane-task/commit/d09d8b4
[b4d84bb]: https://github.com/aaronjae22/ballast-lane-task/commit/b4d84bb
[be013ed]: https://github.com/aaronjae22/ballast-lane-task/commit/be013ed
