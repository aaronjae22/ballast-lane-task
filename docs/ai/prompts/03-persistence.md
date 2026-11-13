# Prompt 03: persistence and read side

- **Iteration:** 2 (persistence and read side)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/02-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** seven PRs: [#15](https://github.com/aaronjae22/ballast-lane-task/pull/15) ADR 0013, [#16](https://github.com/aaronjae22/ballast-lane-task/pull/16) Task model, migration and admin, [#17](https://github.com/aaronjae22/ballast-lane-task/pull/17) ORM repository, [#18](https://github.com/aaronjae22/ballast-lane-task/pull/18) UserLookup and Clock adapters, [#19](https://github.com/aaronjae22/ballast-lane-task/pull/19) `visible_tasks`, [#20](https://github.com/aaronjae22/ballast-lane-task/pull/20) TaskFilter, [#21](https://github.com/aaronjae22/ballast-lane-task/pull/21) overdue and assignee filters

## Why the prompt is written this way

- **The workflow from prompt 02 is kept as it was.** It worked: plan first, small PRs, tiny commits, every commit approved, and the last three PRs needed no follow-up fixes.
- **ADR 0012 sets the shape of the model.** Integer ids from the database, timestamps set by the domain rather than `auto_now`, and "today" in the configured time zone. The prompt points at the ADR instead of restating it, so the model and the domain can't disagree.
- **Two rules now exist twice, so each pair shares its test cases.** Visibility is `can_view()` for writes and `visible_tasks()` for reads; overdue is `Task.is_overdue()` and the `overdue` filter. Each pair is tested against the same rows, so the two copies can't drift.
- **The real adapters are held to the fakes' behaviour.** One repository contract test runs against both the in-memory fake and the ORM repository. That partly answers a gap from iteration 1: nothing type-checks the fakes against the ports.
- **The admin is named as a trap.** Django admin writes straight to the model and would skip every domain rule.
- **Test first still applies, now against Postgres.** Failing integration tests for the repository, the adapters, the selector and the filters come before the code.

## The prompt

```text
You're building iteration 2 (Persistence and read side) of this repo. Before anything else, read AGENTS.md, CLAUDE.md, docs/spec.md (especially sections 3, 4, 5, 9 and 13) and every file in docs/adr/ (especially 0002, 0003 and 0012). Iterations 0 and 1 are merged: look at backend/tasks/domain/, the ports in backend/tasks/application/ports.py, backend/tests/unit/ (fakes.py, builders.py, permission_matrix.py) and the import-linter contracts in backend/pyproject.toml.

Goal: store tasks in Postgres behind the ports from iteration 1, and build the read side (visibility and filters), with integration tests against Postgres. No HTTP yet.

IN SCOPE

1. tasks/models.py and its migration: the Task model.
   - Fields as in spec section 3 and ADR 0012: Django's default integer primary key; title, up to 200 characters; description, default ""; status, with the three values of tasks.domain.status.Status, default to_do; optional due_date; owner and an optional assignee, both foreign keys to the user model; optional completed_at; created_at and updated_at as plain DateTimeFields without auto_now or auto_now_add, because the domain sets them.
   - Indexes from spec section 13: (status, due_date), assignee, owner. Say which of these Django already creates for foreign keys.
   - In the commit that creates tasks/models.py, add tasks.models to import-linter contract 2, as the comment in pyproject.toml says; the same for tasks.admin in the commit that creates it. No other contract change.
2. tasks/admin.py: register Task, read-only. Django admin writes straight to the model and would skip every rule in tasks/domain/ (AGENTS.md: writes go through use cases), so it offers list, search and filters, and no add, change or delete.
3. tasks/infrastructure/: adapters for the ports in tasks/application/ports.py.
   - The ORM TaskRepository: get (None for a missing id), add (returns the task with its new id), save, delete. It maps between the model and the domain Task in one place and stores the domain's timestamps exactly as given.
   - UserLookup: an id is an active user only if that user exists and is_active is true.
   - Clock: timezone.now() and timezone.localdate(), as ADR 0012 says; never date.today() or now().date().
4. tasks/selectors.py: visible_tasks(user) returns a QuerySet of the tasks the user may see (ADR 0003): an admin sees every task; anyone else sees the tasks they own or are assigned to. It uses select_related for owner and assignee, so listing tasks doesn't cause N+1 queries.
5. tasks/api/filters.py: the FilterSet from spec section 5: status (several values), due_after, due_before, overdue (true or false), assignee ("me" or a user id), search (title contains, case-insensitive). Ordering, pagination and views come in iteration 3.
6. Tests under tests/integration/, against Postgres, written first:
   - One repository contract test, run against both InMemoryTaskRepository and the ORM repository: add gives the task an id; get returns it with every field equal, timestamps included; get returns None for a missing id; a change without save() isn't stored; save stores it; delete removes only that task.
   - The adapters: UserLookup for an active, an inactive and an unknown id; Clock.today() in a configured time zone whose date differs from the UTC date.
   - visible_tasks driven by tests/unit/permission_matrix.py: for each role, the task is in the queryset exactly when the "view" row says allowed. Also an unassigned task, and a query-count assertion for listing several tasks with their owner and assignee.
   - The overdue filter tested against the same cases as Task.is_overdue(), shared rather than copied.
   - Every filter, including "me", combinations, and dates on the boundary.
   - At least one write use case from iteration 1 run end to end against the real adapters, with RecordingNotifier as the notifier.
   - Aim for full coverage of the new modules.

OUT OF SCOPE (don't build any of this, not even partially)

- Serializers, views, URLs, pagination, ordering, tasks/api/wiring.py, the DRF exception handler, JWT, throttling (iteration 3)
- The Celery Notifier adapter, email templates, reminders, seed_demo (iteration 4)
- Changes to tasks/domain/ or tasks/application/. If an adapter can't fit a port as it is, stop and tell me.
- Any import-linter change other than the one in item 1, and any coverage setting change

CONSTRAINTS

- Follow AGENTS.md and ADR 0012.
- Where the spec and the ADRs don't decide something, don't guess. List it as a question in the plan, with the option you'd pick and why. At least:
  - What "admin" means on the user model (is_staff or is_superuser). visible_tasks needs it now and iteration 3 maps it to Actor.is_admin, so it has to be one definition in one place.
  - What happens to a user's tasks if the user is deleted (on_delete for owner and assignee).
  - Whether the database should also enforce some domain rules (check constraints on the title length, or on completed_at matching the status), and how that fits "business rules live in tasks/domain/".
  - Whether the repository should lock rows (select_for_update) against lost updates, given that the use cases open no transaction and Django refuses select_for_update outside one.
  - Whether due_after and due_before include the boundary date.
  - Where the shared overdue cases live, and whether test users come from factory-boy (a dev dependency not used yet) or plain helpers.
- No new dependencies.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer (not counting migrations), on its own branch named task/02-NN-short-name, created from an up-to-date main.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first: the repository, each adapter, the selector and the filters each get a test: commit with the failing tests, then a feat: commit that makes them pass. For each test: commit, show the pytest summary lines and why the tests fail (a missing module or attribute, never a typo).
   - Show the public shape: the model's fields, the adapter classes and their method signatures, the selector's signature and the FilterSet's filters. No bodies.
   - List every question and assumption.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Verify, and include the output of each command in your summary. Docker doesn't run on this machine, so the database commands use the local Postgres:
   - cd backend && uv run ruff check . && uv run ruff format --check .
   - cd backend && uv run lint-imports
   - cd backend && DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run python manage.py makemigrations --check --dry-run
   - cd backend && uv run pytest tests/unit --cov-fail-under=0 && uv run coverage report --include='tasks/domain/*,tasks/application/*' --fail-under=100
   - cd backend && DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard uv run pytest   (the full suite, with the 80% gate)
   - uv run --project backend pre-commit run --all-files
4. Finish with a summary: what you created, every deviation from the spec and the ADRs and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

**Plan.** The plan's decisions became ADR 0013 before any code: admins are `is_staff`, read through `User.is_admin`; foreign keys use `PROTECT`; no database check constraints; the repository's `get()` locks the row with `select_for_update`, and the caller holds the transaction; date bounds are inclusive; an invalid filter value is a 400, never ignored. The plan review moved the check that the migration reverses into the PR that adds the migration.

**Build.** Two things closed gaps left open by iteration 1. The ORM repository runs the same contract test as the in-memory fake, so the fake can't drift from the real adapter (#17). Locking the row in `get()` means a load and a later save can't lose a concurrent update. The overdue cases are shared between the domain tests and the filter tests, so both read "overdue" the same way (#21).

**Codex review.**
- #16, P0: the Django admin read tasks without `visible_tasks`. Nothing leaked, since only admins reach the admin, but it was a second definition of visibility. Fixed in #19, where the selector landed: failing tests first ([222f4be](https://github.com/aaronjae22/ballast-lane-task/commit/222f4be)), then the admin reading through it ([dff5be2](https://github.com/aaronjae22/ballast-lane-task/commit/dff5be2)).
- #21, P2: an `assignee` of more than 4,300 digits passed the digit check and made `int()` raise, a 500. Failing tests first ([9dae42b](https://github.com/aaronjae22/ballast-lane-task/commit/9dae42b)), then a 19-digit bound from the column ([313dd15](https://github.com/aaronjae22/ballast-lane-task/commit/313dd15)).
