# ADR 0013: Persistence and read-side conventions

- Status: Accepted
- Date: 2026-11-11

## Context

Iteration 2 stores tasks in Postgres behind the ports from iteration 1, and builds the read side: the `visible_tasks` selector and the task filters. The spec and ADRs 0002, 0003 and 0012 fix the domain rules, but leave these questions about storage and reads open:
- What "admin" means on the user model. `visible_tasks` needs it now, and iteration 3 maps it to `Actor.is_admin`.
- What happens to a user's tasks when the user is deleted.
- Whether the database should also enforce domain rules.
- How a write avoids losing a concurrent update. The use cases open no transaction, and Django refuses `select_for_update` outside one.
- Whether `due_after` and `due_before` include the boundary date, and what an invalid filter value does.
- What the ORM repository does when it's misused. The in-memory fake only asserts in those cases.

The iteration 2 plan review settled these. They bind iteration 3 (wiring, the exception handler) and iteration 4 (`seed_demo`).

## Decision

- **Admin.**
  - A user is an admin when `is_staff` is true. A superuser without `is_staff` is not an admin.
  - It's defined once, as the `User.is_admin` property in `accounts/models.py`. `visible_tasks` reads it, and iteration 3 builds `Actor(id=user.pk, is_admin=user.is_admin)` from it.
- **Deleting users.**
  - `owner` and `assignee` are `on_delete=PROTECT`, so a user who owns or is assigned a task can't be deleted.
  - Users leave by being deactivated (`is_active = False`), which the domain already handles (ADR 0012).
- **No rule constraints in the database.**
  - The database enforces only what the column types say: `title` is `varchar(200)`, required columns are `NOT NULL`, and `owner` and `assignee` are foreign keys.
  - Every rule stays in `tasks/domain/` only. That includes the title length after stripping, and `completed_at` being set exactly when the status is `done`.
  - The repository writes only tasks the domain built, and the admin is read-only (no add, change or delete), so no write path skips the domain.
- **Row locking.**
  - `TaskRepository.get()` serves only the write use cases, because reads go through selectors. So the ORM repository loads with `select_for_update()`. A concurrent write to the same task waits until the first one commits, instead of overwriting it.
  - The caller holds the transaction. Iteration 3 wraps each write use case in `transaction.atomic()` at the composition root. The Notifier's `transaction.on_commit` waits for that same transaction.
  - Called outside a transaction, `get()` raises Django's `TransactionManagementError`. A missing transaction fails loudly instead of silently losing updates.
- **Filters.**
  - `due_after` and `due_before` include the boundary date (`>=` and `<=`), so `due_after=D&due_before=D` means "due on D". A task without a due date matches neither.
  - An invalid value for any filter is an error (400 from iteration 3). That includes `overdue`, which takes only `true` or `false`. An empty value leaves the filter off.
- **The repository on misuse.** These cases aren't part of the port's contract, so only the ORM repository's tests cover them.
  - `add()` given a task that already has an id raises `ValueError`.
  - `save()` updates and never inserts, so it can't bring back a deleted task. If the row is gone, it raises `TaskNotFound` (404).
  - `delete()` of a missing id does nothing.

## Alternatives considered

- **`is_superuser` as admin.** Narrower, but DRF's `IsAdminUser` and access to the Django admin both mean `is_staff`. Two meanings of "admin" in one project would invite mistakes.
- **`CASCADE` on owner and `SET_NULL` on assignee.** Django's usual choices. But deleting a user would delete tasks other people still see, or unassign them, without a use case and without moving `updated_at`.
- **Check constraints for the status values and for `completed_at` matching the status.** Defense in depth, but they're a second copy of domain rules that would have to change with them, which AGENTS.md rules out. A violation would also reach the client as a 500 `IntegrityError`, not a 400.
- **No locking until iteration 3.** Less work now, but writes would be last-write-wins until then, and the lock belongs in the repository.
- **Optimistic locking on `updated_at`.** It holds no lock, but it needs a new domain error for a conflict and a version check on every save.
- **Exclusive date bounds.** That reads "after" and "before" literally, but date-range pickers send inclusive ends, so a range like "due this week" would be off by a day at each end.
- **django-filter's default `BooleanFilter` for `overdue`.** It silently ignores a value like `overdue=yes` and returns every task, and the result looks filtered.

## Consequences

- **Iteration 3** owes the transaction boundary: every write use case runs inside `transaction.atomic()`, or `get()` raises. The first write endpoint's API tests will show a missing transaction.
- **Iteration 3** maps a user to an `Actor` through `user.is_admin`, and nowhere else.
- **Iteration 4:** `seed_demo` creates overdue tasks, which `CreateTask` rejects. So it builds `Task`s directly and stores them through the repository. The database doesn't stop a wrong row there; the seed's tests have to.
- Django admin can't delete a user who has tasks. It lists the tasks that block the deletion, and the user is deactivated instead.
- The database doesn't check a write that bypasses the repository, such as raw SQL or a data migration.
