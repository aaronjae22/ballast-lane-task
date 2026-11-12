# Prompt 01: scaffold

- **Iteration:** 0 (foundation)
- **Tool:** Claude Code in VS Code, plan mode first
- **Branches:** `iter/00-foundation` (first run), then `task/00-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** two runs. The first (branch `iter/00-foundation`, kept locally as `archive/iter-00-first-attempt`) was set aside; the restart landed as five PRs: [#2](https://github.com/aaronjae22/ballast-lane-task/pull/2) Python tooling, [#3](https://github.com/aaronjae22/ballast-lane-task/pull/3) architecture contracts, [#4](https://github.com/aaronjae22/ballast-lane-task/pull/4) Django project, [#5](https://github.com/aaronjae22/ballast-lane-task/pull/5) Docker, [#6](https://github.com/aaronjae22/ballast-lane-task/pull/6) health endpoint

## Why the prompt is written this way

- **It points to the spec instead of restating it**, so there's one source of truth and the prompt stays short enough to review.
- **Scope and non-goals are explicit.** The most common failure of a scaffold prompt is the agent helpfully building features nobody asked for yet.
- **Exact choices where they matter** (versions, contracts, Docker stages), and freedom where they don't.
- **"Done" is a list of commands**, so success is something to verify, not something the agent claims.
- **Plan and questions first.** Nothing is written until the plan, the resolved versions and the assumptions have been reviewed.
- **Versions are checked, not recalled.** The agent resolves them with uv instead of trusting its memory.
- **Small PRs, tiny commits.** The plan splits the work into PRs of about 300 changed lines, each made of commits that do one thing and explain why. Every commit waits for my approval, so each one has been read by a person before it exists.

## The prompt

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

## Review notes

**First run.** The plan, written before any file, found three gaps in this prompt: it asked for `DATABASE_URL` but named no parser (Django has none built in), host port 5432 clashed with my local Postgres, and my local uv was outdated. I chose dj-database-url and a configurable host port defaulting to 5433. The code itself was sound, and the agent adapted on its own to newer tool defaults (ruff, gunicorn, setup-uv). Reviewing the config by hand, not just the green checks, found a bug no test could: `.env.example` set `DJANGO_DEBUG=false`, so copying it to `.env` would have broken compose. I set the run aside anyway because one commit held about 1,400 lines, too much to review properly. I restarted with small PRs and tiny commits, the "How to work" section above.

**Restart, plan review.** The second plan hit the same parser gap, because the prompt still didn't name one, and missed decisions from the first run that weren't written down yet: port 5433, `DJANGO_*` variable names, a configurable `DJANGO_TIME_ZONE`, and ADR 0011. Its layers contract made `api` and `infrastructure` independent siblings, which would have stopped `tasks/api/wiring.py`, the composition root, from importing the adapters. Good catches by the agent: import-linter has no "may import only X" contract, so contract 2 is a denylist; the spec's branch naming was inconsistent; factory-boy doesn't yet declare Django 5.2 support. One fix of mine was incomplete: from the repo root, ruff honours `force-exclude` only as a command-line flag, so the first generated migration was still reformatted until the agent passed the flag in both hooks.

**During the build.**
- CI caught a bad action pin in the agent's own plan in the first PR, before anything depended on it.
- The agent checked each import-linter contract fails on a planted violation before committing it.
- Codex raised two P1s: the settings tests proved the settings import, not that each variable reaches the right setting (#4); nothing ran `entrypoint.sh`, so nothing proved migrations run before the server (#5). Both were fixed with tests that run the real code under controlled inputs.
- The first compose smoke test in CI caught a startup race: compose treated the backend as ready while it was still migrating. A healthcheck on `/api/health/` fixed it.

**What I changed in how I prompt.** The workflow (plan first, small PRs, tiny commits, every commit approved) is now written into every prompt, and every open decision has to come back as a question with a proposed answer. Prompt 02 starts from that.

**Left open.** The entrypoint migrates on every start, which needs a separate step once several containers share the image. The smoke test runs the dev target, so the prod image is only built. `/api/health/` checks the database, so it is a readiness check, not a liveness check. Three agent commits were typed `fix:` for CI changes where `ci:` fits; they stay, since history isn't rewritten.
