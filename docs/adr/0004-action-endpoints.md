# ADR 0004: Action endpoints for status and assignment changes

- Status: Accepted
- Date: 2026-11-10

## Context

Status and assignment changes have their own rules and side effects: only some people may make them, completing records a timestamp, and assigning sends an email.

## Decision

- `POST /api/tasks/{id}/assign/`, `/start/`, `/complete/`, `/reopen/`, each mapped to one use case.
- `PATCH /api/tasks/{id}/` changes only title, description and due date.
- An invalid transition returns 409 Conflict.

## Alternatives considered

- **PATCH with `status` and `assignee` fields.** Fewer routes, but it hides several use cases inside one generic update and mixes owner-only and assignee rules in one endpoint.

## Consequences

- Each endpoint has one permission rule and one side effect, and each shows up on its own in Swagger.
- A few more routes and a few more tests.
