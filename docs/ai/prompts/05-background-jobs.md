# Prompt 05: background jobs and seed data

- **Iteration:** 4 (background jobs and seed data)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/04-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** _PR links added after the run_

## Why the prompt is written this way

- **The workflow is unchanged.** Plan first, small PRs, tiny commits, every commit approved, an ADR before code when a decision binds later work.
- **The swap was prepared in iteration 3.** The Celery notifier replaces one line in `wiring.notifier()`, and the API tests use a recording fake, so they shouldn't change. If they have to, something leaked.
- **Two traps are named up front.** The entrypoint migrates on every container start, and three containers will now share the image. And `seed_demo` can't create overdue tasks through `CreateTask`, so ADR 0013 already says it goes through the repository, with its own tests standing in for the database's missing checks.
- **Two ways to verify, because this machine may not run Docker.** The tests never need a broker, a worker or an SMTP server. The end-to-end check (an assignment in Swagger arriving in Mailpit) does, so the prompt asks for both a compose path and a host path with Homebrew's Redis and Mailpit, and the agent is told which one is available.
- **Email is a side effect that can't be taken back.** So the prompt asks what happens when a task changes between the commit and the worker picking up the job, and when sending fails.

## The prompt

```text
You're building iteration 4 (Background jobs and seed data) of this repo. Before anything else, read AGENTS.md, CLAUDE.md, docs/spec.md (especially sections 3, 7, 9, 10 and 13) and every file in docs/adr/ (especially 0009, 0012, 0013 and 0014). Iterations 0 to 3 are merged: look at tasks/application/ports.py (the Notifier port), tasks/infrastructure/notifications.py (LoggingNotifier), tasks/api/wiring.py (notifier()), tasks/infrastructure/repositories.py, config/celery.py, config/settings.py, backend/entrypoint.sh, docker-compose.yml, the CI workflow, and the tests.

Goal: the assignment email and the due-tomorrow reminders run through Celery, compose runs a worker and Beat from the same image, and seed_demo fills a fresh stack with demo data, idempotently.

IN SCOPE

1. The Celery Notifier adapter in tasks/infrastructure/: task_assigned() queues a Celery task inside transaction.on_commit, so a rolled-back assignment sends nothing (spec section 7). wiring.notifier() returns it instead of LoggingNotifier, and LoggingNotifier goes (ADR 0014).
2. Celery tasks:
   - Send the assignment email to the assignee, rendered from templates (plain text, and HTML if you think it's worth it).
   - The due-tomorrow reminder: Celery Beat runs it once a day; each assignee gets one digest of their tasks due tomorrow that aren't done. "Tomorrow" is the day after the Clock's today, in the configured TIME_ZONE (ADR 0012), and the schedule runs in that time zone too.
   - Tasks take ids, not objects, and load what they need when they run.
3. compose: worker and beat services from the backend image (spec section 10), started after the backend is healthy. Only one container runs migrate and seed_demo; worker and beat never do. Beat's schedule file must not land in the mounted source folder.
4. seed_demo (spec section 7), a management command in accounts/ (spec section 4), run by the backend entrypoint when SEED_DEMO=true (the local default in compose, off everywhere else):
   - An admin and three users with known passwords, and about 25 tasks across every status and due-date bucket (overdue, today, tomorrow, next week, none), so every filter shows results.
   - Idempotent: running it twice creates nothing new.
   - Overdue tasks can't come from CreateTask, which rejects past due dates. As ADR 0013 says, the seed builds domain Tasks and stores them through the repository, so its tests must check the rows the database won't (statuses, completed_at matching the status, title rules).
   - The README gets the demo credentials (spec section 2 traceability table).
5. Tests, written first:
   - The adapter queues exactly one job after commit and none after a rollback (django_capture_on_commit_callbacks).
   - The email tasks against Django's in-memory email backend: recipients, subject, body, and what happens in the edge cases you decide on below.
   - The reminder: who gets a digest and what's in it, with a fixed clock, including the time-zone boundary and done or inactive cases.
   - seed_demo: the users, every bucket covered, idempotent on a second run, and the rows valid by the domain's rules.
   - The API tests still pass without changes.

OUT OF SCOPE (don't build any of this, not even partially)

- Anything in frontend/ (iterations 5 and 6), the prod compose override and nginx (iteration 7)
- Changes to tasks/domain/ and tasks/application/. If the port doesn't fit the Celery adapter, stop and tell me.
- New API endpoints, and changes to the import-linter contracts or the coverage settings

CONSTRAINTS

- Follow AGENTS.md and the ADRs. If something here conflicts with them, stop and say so.
- Where the spec and the ADRs don't decide something, don't guess. List it as a question in the plan, with the option you'd pick and why. At least:
  - How migrate and seed_demo run once while backend, worker and beat share the image (the entrypoint migrates on every start today).
  - What the email job does if, by the time it runs, the task was deleted, reassigned again, or the assignee was deactivated or has no email address.
  - Retries when sending fails, and whether a retry can send the same email twice.
  - Whether the daily reminder can send twice (for example after Beat restarts), and whether that matters.
  - How seed_demo stays idempotent (what identifies a seeded user or task), whether its due dates are relative to the day it runs, and what keeps it out of production.
  - How the tests run Celery tasks without a broker, and which Celery settings the plan adds (serializer, time zone, eager mode in tests or not).
  - Whether the CI compose smoke test should also prove the email path (for example by reading Mailpit's API after an assignment).
  - Which of these answers belong in an ADR (0015) before the code.
- No new dependencies unless you say why in the plan. Beat's schedule can live in settings; a database-backed scheduler isn't needed.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer (not counting migrations and uv.lock), on its own branch named task/04-NN-short-name, created from an up-to-date main. If an ADR is needed, it comes first, docs only.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first: a test: commit with the failing tests, then a feat: commit that makes them pass. For each test: commit, show the pytest summary lines and why the tests fail (a missing module or attribute, never a typo).
   - Show the public shape: the adapter, the Celery tasks and their arguments, the Beat schedule, the email templates, seed_demo's options, the compose services and the entrypoint's steps, and the settings you add. No bodies.
   - List every question and assumption.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Verify, and include the output of each command in your summary. The tests use the local Postgres and need no broker, worker or SMTP server:
   - cd backend && uv run ruff check . && uv run ruff format --check .
   - cd backend && uv run lint-imports
   - cd backend && DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run python manage.py makemigrations --check --dry-run
   - cd backend && DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run python manage.py spectacular --validate --fail-on-warn --file /dev/null
   - cd backend && uv run pytest tests/unit --cov-fail-under=0 && uv run coverage report --include='tasks/domain/*,tasks/application/*' --fail-under=100
   - cd backend && DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run pytest   (the full suite, with the 80% gate)
   - uv run --project backend pre-commit run --all-files
   - The end-to-end check (spec section 13: an assignment made in Swagger shows up in Mailpit, and seed_demo run twice creates no duplicates). Write the steps for both ways of running it, and I'll tell you which one this machine has:
     A. Docker: docker compose up --build --wait, then Swagger at http://localhost:8000/api/docs/ and Mailpit at http://localhost:8025, and the reminder triggered by hand (say how).
     B. No Docker: Redis and Mailpit from Homebrew (brew install redis mailpit; say how to start them), then runserver, a worker and Beat in separate terminals against the local Postgres, with the same Swagger and Mailpit steps.
     Put the host commands for the worker and Beat in the Commands section of AGENTS.md as well.
4. Finish with a summary: what you created, every deviation from the spec and the ADRs and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

_Filled in after the run: what the output got right, what was wrong, and what I changed._
