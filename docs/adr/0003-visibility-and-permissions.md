# ADR 0003: Task visibility and permissions

- Status: Accepted
- Date: 2026-11-10

## Context

"Assign tasks to users" means deciding who can see and change which tasks. The brief doesn't say.

## Decision

- You see tasks you own or are assigned to; an admin sees all tasks.
- The owner edits, reassigns and deletes; the assignee changes status; an admin can do anything. The full matrix is in `docs/spec.md` section 3.
- A task outside your visibility returns **404**, not 403.
- **Overdue** is computed from the due date and status, never stored.
- Permission rules live in the domain; visibility lives in one selector, `visible_tasks(user)`, applied to every read.

## Alternatives considered

- **Shared board where everyone sees everything.** Simpler, but it leaves almost no permission logic to design or test.
- **403 for tasks you can't see.** Tells a caller that the task exists.
- **An `overdue` status set by a scheduled job.** Can be stale between runs and adds a job whose only purpose is to flip state.

## Consequences

- The permission matrix becomes one parametrized API test.
- List endpoints are scoped by default, so a missing filter can't leak tasks.
