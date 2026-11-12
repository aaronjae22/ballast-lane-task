# Prompt 02: domain and use cases

- **Iteration:** 1 (domain and use cases, test first)
- **Tool:** Claude Code in VS Code, a fresh session, plan mode first
- **Branches:** `task/01-NN-short-name`, one per PR
- **The agent reads:** `AGENTS.md`, `CLAUDE.md`, `docs/spec.md`, `docs/adr/`
- **Result:** five PRs, merged at `7d34c92`: [#8](https://github.com/aaronjae22/ballast-lane-task/pull/8) Task entity, [#9](https://github.com/aaronjae22/ballast-lane-task/pull/9) transitions, permissions and assignment, [#10](https://github.com/aaronjae22/ballast-lane-task/pull/10) ports, fakes and CreateTask, [#11](https://github.com/aaronjae22/ballast-lane-task/pull/11) UpdateTask and AssignTask, [#12](https://github.com/aaronjae22/ballast-lane-task/pull/12) status changes, delete and the use-case matrix. The decisions the plan settled are recorded in ADR 0012.

## Why the prompt is written this way

- **The workflow from iteration 0 is written in, not renegotiated.** Plan first, small PRs, tiny commits, every commit approved: the first run of prompt 01 showed what happens without them (one 1,400-line commit nobody could review).
- **The spec holds the rules; the prompt names the traps.** Overdue tasks must stay editable, a task you can't see is "not found" rather than "not allowed", and the assignment email has exceptions. These are the rules an agent most easily gets subtly wrong.
- **Gaps become questions.** In iteration 0 the plan surfaced gaps in my own prompt before any code existed. Here the prompt asks for every undecided point as a question with a proposed answer, instead of a silent choice.
- **Shape before code.** The plan shows the domain and port signatures without bodies, so the design can be reviewed in minutes before tests are written against it.
- **Test first, visible in history.** Each rule gets a failing-test commit before the code that passes it.
- **A hard boundary.** No Django, no database, no HTTP. import-linter enforces it, and the agent is told never to touch the contracts.

## The prompt

```text
You're building iteration 1 (Domain and use cases) of this repo. Before anything else, read AGENTS.md, CLAUDE.md, docs/spec.md (especially sections 3, 4, 7, 9 and 13) and every file in docs/adr/ (especially 0002, 0003, 0004 and 0011). Iteration 0 is merged: look at backend/tasks/, backend/tests/ and backend/pyproject.toml to see the empty layer packages, the test layout and the import-linter contracts.

Goal: every business rule in spec section 3 and every write use case, in plain Python, test first, with no database, no Django and no HTTP.

IN SCOPE

1. tasks/domain/ (standard library only; dataclasses and type hints):
   - Status: to_do, in_progress, done.
   - Task, with the fields in spec section 3 and the rules that belong to a task: the title is 1-200 characters; the due date can't be set to a date before today; overdue is computed (due date before today and status isn't done), never stored; the transitions start, complete and reopen, with their effect on completed_at.
   - The acting user: a small value object with the user's id and whether they're an admin.
   - The permission rules from the matrix in spec section 3, including visibility: the owner, the assignee and an admin can see a task; anyone else can't.
   - The assignment-email rule from spec section 3: an email is due only when the assignee changes to someone other than the person making the change.
   - Errors: NotAllowed, TaskNotFound, InvalidTransition, DomainValidationError.
   - "Today" and "now" are passed in as values. The domain never reads a clock.

2. tasks/application/ (imports only tasks.domain):
   - Ports as typing.Protocol: TaskRepository, UserLookup (is this user id an active user?), Notifier (a task was assigned to someone), Clock (now, and today in the configured time zone).
   - Use cases, one class each, with their dependencies passed to the constructor: create task (with an optional assignee), update task (title, description and due date only), assign (assign, reassign, unassign), start, complete, reopen, delete.
   - A task the acting user can't see raises TaskNotFound, not NotAllowed, so the API can answer 404 without revealing that the task exists.
   - Editing a task that is already overdue must still work: the past-date rule applies only when the due date is being set to a new value.
   - The Notifier is called only when the assignment-email rule says so, on create and on assign.

3. In-memory fakes for the four ports, under tests/unit/ (not in the application package).

4. Unit tests under tests/unit/, written first:
   - Every rule in spec section 3, with the boundaries: a title of 200 vs 201 characters and an empty title; a due date of today vs yesterday; every transition that isn't allowed.
   - The permission matrix as one parametrized test whose rows read like the table in spec section 3: action x owner / assignee / admin / anyone else -> allowed, NotAllowed or TaskNotFound.
   - The assignment email: assigning someone else sends one; self-assignment, unassigning and reassigning to the same person send none; creating a task with someone else as assignee sends one; with yourself, none.
   - Unit tests never touch the database. Aim for 100% coverage of tasks/domain and tasks/application.

OUT OF SCOPE (don't build any of this, not even partially)

- The Django Task model, migrations, admin, the ORM repository, selectors and visible_tasks (iteration 2)
- Serializers, views, URLs, tasks/api/wiring.py and the DRF exception handler (iteration 3)
- The Celery Notifier adapter, email templates and reminders (iteration 4)
- Any change to the import-linter contracts or the coverage settings. If one blocks you, stop and tell me.

CONSTRAINTS

- Follow AGENTS.md: architecture rules, testing rules, git rules, scope rules.
- Use the spec's domain language: owner, assignee, due date, overdue, start, complete, reopen.
- Where the spec doesn't decide something (for example: how a new task gets its id, who sets created_at and updated_at, whether a whitespace-only title is valid, whether completing a task that's already done is an error), don't guess. List it as a question in the plan, with the option you'd pick and why.
- No new dependencies.

HOW TO WORK

1. Plan first, and wait for my approval before writing files.
   - Split the work into a sequence of small PRs. Each PR is one task of about 300 changed lines or fewer, on its own branch named task/01-NN-short-name, created from an up-to-date main.
   - For each PR, list its commits (Conventional Commits subject plus one line each) and the files in each commit. Test first: each rule or use case gets a test: commit with the failing tests, then a feat: commit that makes them pass.
   - Show the public shape you propose for the domain and the ports: classes, fields and method signatures, no bodies.
   - List every question and assumption.
2. Work one PR at a time:
   - Tiny commits, one concern each, ideally under about 150 changed lines. Each commit body has 2-5 lines on why (the reason for each non-obvious choice), never a list of files. Before each commit, show git diff --staged --stat and a 2-3 line note on what the commit does; every commit waits for my approval.
   - When a PR's commits are done, run the checks below, then push the branch and open the PR against main with gh pr create, with a short title and a description with these sections: Summary (what and why), Commits (one line each), How to verify (commands and their results), Out of scope. The push and the PR both wait for my approval.
   - Wait until I tell you the PR is merged. Then switch to main, pull, and start the next PR.
3. Verify, and include the output of each command in your summary:
   - cd backend && uv run ruff check . && uv run ruff format --check .
   - cd backend && uv run lint-imports
   - cd backend && uv run pytest tests/unit   (no database needed; report the coverage of tasks/domain and tasks/application)
   - cd backend && uv run pytest   (the full suite; the database tests need the compose db or DATABASE_URL)
   - uv run --project backend pre-commit run --all-files
4. Finish with a summary: what you created, every deviation from the spec and why, anything you weren't sure about, anything you noticed but left out of scope, and an ADR proposal for any decision the spec didn't cover.
```

## Review notes

**Plan.** The first plan matched the spec and answered the four questions this prompt named (task id, timestamps, whitespace-only titles, completing a done task), plus five more it found itself: an empty description, "set to a new value" for the assignee too, one error for unknown and inactive assignees, the order of checks, and hard delete. I accepted every proposed answer; they became ADR 0012. The plan review added five changes:
- Make 100% coverage of domain and application a failing check through command-line flags, not a number to read.
- Show why each failing-test commit fails, so a typo can't pass for test-first.
- Document in `access.py` that writes check visibility with the domain rule, because the Codex review rules flag any task read that skips `visible_tasks`.
- Pull `main` before PR 1.
- Name the fixtures file.

The second round applied all five and changed nothing else.

**Build.** 26 commits, every rule as a failing-test commit followed by its code, 171 unit tests, 100% line and branch coverage of `tasks/domain` and `tasks/application`. What went wrong:
- PR #8: CI's ruff flagged import order (I001). Ruff counts a module as first-party only once its file exists, so a test written before its module was sorted as third-party; ruff's local cache hid it. The agent fixed the file, then the cause, with `known-first-party`, and no later PR hit it.
- PR #9: pytest 9.2 warned that passing an iterator to `parametrize` will fail in pytest 10. Fixed with a list.
- Every PR ran over its size target, roughly 320 to 430 lines against about 230 to 300 planned, mostly in tests.
- Two more test-only changes were typed `fix:`.

**How the output was validated.** Besides CI and Codex on every PR, I reran each merged PR's unit tests on a clean copy with warnings as errors. For the use-case permission matrix, which passes the moment it's added, I broke the code on purpose: with `UpdateTask` checking the change-status permission, exactly one case failed, the assignee editing. The agent ran the same check before committing.

**Codex review.** _To add: findings on #8 to #12 and their fixes._

**Left open, carried into iteration 2.** No static type checker runs in CI, so nothing checks that the fakes, and later the adapters, match the ports. `AssignTask` has no test proving access is checked before the values, as `UpdateTask` has. Loading a task and saving it later can lose a concurrent update. `visible_tasks` must be tested against the same matrix rows as the domain.
