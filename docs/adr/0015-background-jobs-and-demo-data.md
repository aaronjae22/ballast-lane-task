# ADR 0015: Background jobs and demo data

- Status: Accepted
- Date: 2026-11-12

## Context

Iteration 4 sends the assignment email and the due-tomorrow reminders through Celery, runs a worker and Beat from the backend image (ADR 0009), and adds `seed_demo`. Spec sections 7, 10 and 13 and ADRs 0012–0014 fix what these do, but leave these questions open:
- How `migrate` and `seed_demo` run only once now that three containers share the image, and the entrypoint migrates on every start.
- What the email job does when the task or the assignee has changed by the time it runs.
- Retries when sending fails, and whether an email can go out twice.
- Whether the daily reminder can go out twice, and how its recipients are found.
- How `seed_demo` stays idempotent, what its dates are relative to, and what keeps it and its known passwords out of production.
- How the tests run Celery tasks without a broker, and which Celery settings are needed.
- How far two AGENTS.md rules reach: jobs queued inside `transaction.on_commit`, and every task read applying `visible_tasks(user)`.

The iteration 4 plan review settled these. They bind iteration 7 (the prod override and the Cloud Run worker pool) and every later review.

## Decision

- **One container migrates and seeds.**
  - The entrypoint has two switches, and each takes only the literal `true`:
    - `MIGRATE_ON_START` (default `true`) runs `migrate`.
    - `SEED_DEMO` (default `false`) runs `seed_demo` after it.
  - Compose's `backend` sets `SEED_DEMO=true`. `worker` and `beat` set `MIGRATE_ON_START=false`, and start only once `backend` is healthy, so the schema and the seed are already there.
  - The default stays `true` so the backend and the prod image keep today's behaviour. Every other process that runs the image turns it off.
- **The assignment email re-checks when it runs.**
  - The job takes `(task_id, assignee_id)` and loads both. It sends only if the user is active, has an email address, and is still the task's assignee. It reads the task through `visible_tasks(user)`.
  - Otherwise it logs at INFO and stops, without retrying. That covers a deleted task, one reassigned or unassigned since, a deactivated assignee, and a missing email address.
  - The email shows the task as it is when it's sent. If a task is reassigned A→B→A quickly, A can get two emails.
- **Retries and duplicates.**
  - A send that fails with `OSError` is retried. That includes connection errors, timeouts and `SMTPException`. `SMTPRecipientsRefused` isn't retried, because it's permanent.
  - At most 5 retries, with exponential backoff and jitter, capped at 10 minutes. `EMAIL_TIMEOUT` is 10 seconds, so a hung SMTP server can't hold a worker.
  - Celery acks before running, its default. A worker that dies mid-send loses that email rather than sending it twice.
  - An email can still go out twice in one case: the SMTP server accepted it and its reply was lost. That's accepted.
  - The adapter queues inside `transaction.on_commit(..., robust=True)`. If the broker is down at commit time, Django logs the error and the request still succeeds. The assignment is saved and the email is lost, with a log entry. A committed write never turns into a 500.
- **The due-tomorrow reminder.**
  - Beat runs it daily at 08:00 in `TIME_ZONE` (`CELERY_TIMEZONE = TIME_ZONE`). "Tomorrow" is the Clock's today plus one day (ADR 0012).
  - The Beat task finds the recipients in one query and queues one digest job per recipient with `(user_id, day)`. The day is an ISO date, computed once. A failed send retries one person's digest, not everyone's.
  - Recipients are active users with an email address who are assigned a task due that day that isn't done. Self-assigned tasks count: the "someone else" rule is about assignment emails, not due dates. Each digest re-reads that user's tasks and sends nothing if none are left.
  - The schedule lives in settings. Beat's schedule file goes to the system temp directory (`CELERY_BEAT_SCHEDULE_FILENAME` overrides it), never into the mounted source folder.
  - A Beat restart doesn't send twice: a crontab entry fires only when the stored last run is older than the latest slot, never just because Beat started. A second digest can still come from two Beat processes, a manual trigger on the same day, or a retry after a lost SMTP reply. There's no dedupe store. A repeated reminder is a nuisance, and a lost one is worse. Exactly one Beat runs.
- **Scope of two AGENTS.md rules.**
  - **Jobs are queued inside `transaction.on_commit`** when they're the side effect of a write, so a rolled-back change sends nothing. The reminder's fan-out writes nothing and runs outside any transaction, so it calls `.delay()` directly.
  - **Every task read applies `visible_tasks(user)`** when it's made on behalf of a user. Finding the reminder's recipients is a system job that reads across users, so `reminder_recipients()` doesn't apply it, and its docstring says why. Each digest's own read does go through `visible_tasks(user)`, as does the assignment email's.
- **`seed_demo`.**
  - It creates an admin (`is_staff` and `is_superuser`) and three users, each with a full name and an `@example.com` address.
  - Users are found by username, and an existing user is never changed, so the seed can't reset a real account's password.
  - Tasks are created only if no demo user owns a task yet, all at once in one transaction. A rerun creates nothing, and edits and deletions to demo tasks survive restarts. `docker compose down -v` starts over.
  - Due dates are relative to the Clock's today when it runs, so a fresh stack fills every bucket: overdue, today, tomorrow, next week and none. They age from then on.
  - Following ADR 0013, it builds domain `Task`s and stores them through the repository, because `CreateTask` rejects past due dates. Each task comes from `Task.create()` with a backdated today and now, then `start()` or `complete()`. So the domain still strips titles, allows only valid transitions and sets `completed_at`. It sends no email. Its tests check the rows the database doesn't.
  - **Passwords.** Every demo user's password is `SEED_DEMO_PASSWORD`, read when the seed runs, defaulting to `demo-password`. The README documents the default for local use. **A deployment anyone else can reach must set its own `SEED_DEMO_PASSWORD`**: the seed creates a superuser, and the default is public.
  - Only the entrypoint with `SEED_DEMO=true` runs it. The Dockerfile and the settings never turn it on. There's no DEBUG guard, because iteration 7 runs the prod image with seeded data.
- **Tests and settings.**
  - No test needs a broker, a worker or an SMTP server. Adapter tests replace `.delay` with a recorder. Job tests call `.apply()`, which runs the task in-process, retries included. Email goes to Django's in-memory backend.
  - `task_always_eager` is never set globally: it would hide the on-commit and serialization boundary.
  - Celery uses JSON only (`task_serializer`, `accept_content`), ignores results (there's no result backend), and retries the broker connection on startup. Tasks have explicit names and take ids and ISO dates, never objects.
- **The CI smoke test proves the email path.** With the compose stack up, it runs `seed_demo` again and expects nothing new. It assigns a task over HTTP and reads the email from Mailpit's API, triggers the reminder and reads the digests, and checks that the worker and beat didn't migrate.

## Alternatives considered

- **`MIGRATE_ON_START` off by default.** A forgotten flag couldn't cause a concurrent migrate, but the backend and the prod image would have to opt in.
- **A one-shot `migrate` service in compose** that the others wait for. It's clean in compose, but the spec has the backend's entrypoint do it, and Cloud Run has no such dependency.
- **Overriding the entrypoint for the worker and beat.** It works in compose, but every other place that runs the image would have to remember it.
- **Sending what the task was at assignment time.** It would need the title and due date in the message, and an email for a task that's no longer the user's.
- **Acks late (`acks_late`).** A worker crash would resend instead of losing the email. Duplicates are the more visible failure.
- **Letting a broker error at commit time raise.** The client would get a 500 for a write that was saved.
- **Sending every digest inside the Beat task.** One job, but a retry would resend to everyone already done.
- **A table or cache key to dedupe reminders.** It stops repeats, but needs a write before or after every send, and either order loses or repeats an email when it fails.
- **Wrapping the fan-out's `.delay()` calls in `on_commit`.** Outside a transaction it runs at once, so it would satisfy the rule's wording and do nothing.
- **Running the recipients query per user through `visible_tasks`.** It satisfies the rule's wording, but needs a query per user to find out who's a recipient.
- **Matching seeded tasks one by one by title.** A demo user's edited title would come back as a duplicate on the next restart.
- **Fixed seed dates.** Reproducible, but a fresh stack a month later would have no "today" or "tomorrow" tasks.
- **A fixed, documented demo password.** Simpler, but a public deployment of the seeded image would publish a superuser login.
- **Refusing to seed when DEBUG is off.** Safer by default, but iteration 7 needs the prod image seeded.
- **A database-backed scheduler (django-celery-beat).** One more dependency for a single daily entry.

## Consequences

- **Iteration 7:** the prod override and any Cloud Run worker pool set `MIGRATE_ON_START=false` on every process except one. Any reachable deployment that seeds sets its own `SEED_DEMO_PASSWORD`. Exactly one Beat runs.
- An assignment saved while the broker is down sends no email. The log says so, and nothing retries it.
- A reminder can arrive twice in the rare cases above, and never because Beat restarted.
- Demo tasks' due dates drift as days pass, and overdue grows. Recreating the volumes reseeds them.
- Reviews have a stated scope for the `on_commit` and `visible_tasks` rules. A system job that reads across users says so in its docstring.
- The dev worker doesn't reload on code changes. `docker compose restart worker beat` picks them up.
