# Architecture decision records

One short file per decision that a reviewer might reasonably ask "why?" about. Records are never edited after they're accepted; a changed decision gets a new record that supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-backend-django-drf.md) | Django + DRF for the backend | Accepted |
| [0002](0002-architecture-strict-writes-plain-reads.md) | Strict layers on the write path, plain Django on the read path | Accepted (contract list superseded by [0011](0011-import-linter-contracts.md)) |
| [0003](0003-visibility-and-permissions.md) | Task visibility and permissions | Accepted |
| [0004](0004-action-endpoints.md) | Action endpoints for status and assignment changes | Accepted |
| [0005](0005-api-docs-drf-spectacular.md) | drf-spectacular instead of drf-yasg for API docs | Accepted |
| [0006](0006-jwt-refresh-cookie-same-origin.md) | JWT with an in-memory access token and an httpOnly refresh cookie, served from one origin | Accepted |
| [0007](0007-frontend-react-typescript-mantine.md) | React + TypeScript + Mantine, built to static files | Accepted |
| [0008](0008-python-tooling-uv-ruff-precommit.md) | uv, ruff and pre-commit with local hooks | Accepted |
| [0009](0009-docker-multi-stage-one-image.md) | Multi-stage Docker images, one backend image for every process | Accepted |
| [0010](0010-ai-workflow-builder-reviewer.md) | AI-assisted workflow with separate builder and reviewer | Accepted |
| [0011](0011-import-linter-contracts.md) | import-linter contracts as built | Accepted (supersedes 0002's contract list) |
| [0012](0012-domain-conventions-time-identity-unchanged-values.md) | Domain conventions for time, identity and unchanged values | Accepted |

## Template

```markdown
# ADR NNNN: Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
What forces the decision.

## Decision
What we do.

## Alternatives considered
What else was on the table, and why not.

## Consequences
What gets easier, what gets harder.
```
