# ADR 0011: import-linter contracts as built

- Status: Accepted
- Date: 2026-11-11
- Supersedes: the contract list in [ADR 0002](0002-architecture-strict-writes-plain-reads.md) (the rest of 0002 stands)

## Context

ADR 0002 lists three rules for import-linter: `tasks.domain` imports nothing from Django, DRF or Celery; `tasks.application` imports only `tasks.domain`; neither imports `tasks.infrastructure` or `tasks.api`. Turning them into contracts in iteration 0 ran into two constraints in import-linter 2.16:

- It has no contract type for "may import only X". It offers `forbidden`, `independence`, `layers`, `protected` and `acyclic_siblings`, all of which say what can't be imported, not what can.
- A `forbidden` contract fails if it names an internal module that doesn't exist yet, such as `tasks.models` before the model is written.

## Decision

Three contracts in `backend/pyproject.toml`, run by pre-commit and CI:

1. **Forbidden:** `tasks.domain` must not import `django`, `rest_framework` or `celery`.
2. **Forbidden:** `tasks.application` must not import `django`, `rest_framework`, `celery`, or any `tasks` module outside `tasks.domain` (`tasks.infrastructure`, `tasks.api`, `tasks.selectors`). `tasks.models` and `tasks.admin` are added to the list in the commit that creates them.
3. **Layers**, strictly ordered: `tasks.api` > `tasks.infrastructure` > `tasks.application` > `tasks.domain`. A layer may import the layers below it, never above. `tasks.api` sits above `tasks.infrastructure`, not beside it, because `tasks/api/wiring.py` is the composition root and has to import the infrastructure adapters.

Each contract was checked to fail on a planted violation before it was committed.

## Alternatives considered

- **`tasks.api | tasks.infrastructure` as independent siblings.** It treats both as outer adapters, but it forbids the composition root from importing the adapters it wires.
- **A `tasks.*` wildcard in contract 2.** It can't cover modules that don't exist yet without also matching `tasks.domain`, which the application must be able to import.
- **A custom contract type that allowlists imports.** That's extra code to maintain for one rule that review already covers.

## Consequences

- Contract 2 is a denylist. A third-party import in `tasks/application/` that isn't listed (for example `requests`) passes the linter. The Architecture rules in `AGENTS.md` (Code Review Rules) catch it in review.
- Iteration 2 must extend contract 2 when it adds `tasks/models.py` and `tasks/admin.py`. A comment in the contract says so.
- Infrastructure can't import the API layer, so adapters never depend on serializers or views.
