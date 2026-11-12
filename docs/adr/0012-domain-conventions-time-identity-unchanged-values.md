# ADR 0012: Domain conventions for time, identity and unchanged values

- Status: Accepted
- Date: 2026-11-11

## Context

Spec section 3 gives the task rules but leaves several things open:
- It says `created_at` and `updated_at` are "automatic" without saying who sets them.
- It doesn't say how a new task gets its id, or whether a whitespace-only title is valid.
- It says a due date "can't be set to a date in the past" while "tasks already overdue stay valid", without saying what happens when an edit sends the current value again.
- It lists the four domain errors but not which one wins when several apply.

Iteration 1 settled these in `tasks/domain/` and `tasks/application/`, and the plan review approved them. Iterations 2 and 3 have to follow them in the model, the repository, the serializers and the error mapping.

## Decision

- **Identity.** The repository assigns the id when it stores a new task (`TaskRepository.add()` returns the task with its id). `Task.id` is `None` until then.
- **Time.** The domain never reads a clock; the use cases get `now()` and `today()` from the `Clock` port and pass them in.
  - "Today" is `Clock.today()`, the date in the configured `TIME_ZONE`, never `now().date()`.
  - A new task gets `created_at = updated_at = now`. Every successful write sets `updated_at = now`, even when no value changed, as Django's `auto_now` would on every save.
- **Titles.** Leading and trailing whitespace is stripped before the 1–200 character check, and the title is stored stripped, so a whitespace-only title is empty and rejected.
- **Unchanged values.** The past-due-date rule and the active-assignee rule apply only when the value changes:
  - Re-sending a task's current past due date is allowed.
  - Re-sending its current assignee is allowed, even if that user has since been deactivated.
  - Clearing the due date or unassigning is always allowed.
- **Order of checks.**
  - The order is: missing or not visible (`TaskNotFound`), then permission (`NotAllowed`), then the rule (`DomainValidationError` or `InvalidTransition`).
  - Missing and not visible raise the same error with the same message.
  - A write that fails any check saves nothing and sends no email.

## Alternatives considered

- **UUIDs generated in the domain.** The domain wouldn't depend on the store for ids, but they would differ from the integer keys Django uses for every other table.
- **`auto_now` and `auto_now_add` on the model.** This is Django's default, but the ORM would overwrite the values the domain sets, and unit tests couldn't control time without a database.
- **`now().date()` as today.** Simpler, but wrong for part of every day in any time zone other than UTC.
- **Keeping title whitespace as sent.** DRF's `CharField` trims by default, so the API and the domain would disagree about what a valid title is.
- **Checking every value sent on every edit.** An overdue task couldn't be edited without changing its due date, which contradicts the spec, and a deactivated assignee would block unrelated edits.
- **Checking values before permission.** A caller who can't see a task could tell from a 400 that the task exists.
- **Setting `updated_at` only when a value changes.** More precise, but every write would need a field-by-field comparison, and it would differ from what `auto_now` does.

## Consequences

- **Iteration 2:**
  - The `Task` model uses Django's default integer primary key, and plain `DateTimeField`s for `created_at` and `updated_at` without `auto_now` or `auto_now_add`. The repository writes the domain's values.
  - The `Clock` adapter returns `timezone.now()` and `timezone.localdate()`.
- **Iteration 3:**
  - Serializers check only the shape of the input and leave these rules to the domain, so the two can't disagree.
  - The exception handler gives 404 before 403, and 403 before 400 or 409, because the use cases raise in that order.
- **`updated_at` moves on writes that change nothing,** such as re-sending the current assignee. Anyone using it as "last real change" should know that.
- **One place to look:** the rules that depend on "a new value" live in `Task.edit()` and `Task.assign()`.
