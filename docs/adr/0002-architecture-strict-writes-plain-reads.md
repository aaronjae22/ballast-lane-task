# ADR 0002: Strict layers on the write path, plain Django on the read path

- Status: Accepted
- Date: 2026-11-10

## Context

Clean Architecture is the first evaluation criterion. Django's default style puts business logic in models, serializers and views, which ties rules to the ORM and HTTP. Applying ports and adapters to everything, though, means rebuilding Django's filtering and pagination behind repository interfaces for a mostly-CRUD app.

## Decision

Apply the dependency rule strictly where business rules live, and use plain Django where there are none.

- **Writes** (create, update, assign, start, complete, reopen, delete) go through use cases in `tasks/application/`. They work on a plain-Python `Task` in `tasks/domain/` and reach the outside world only through ports: `TaskRepository`, `UserLookup`, `Notifier`, `Clock`. The Django ORM and Celery implement those ports in `tasks/infrastructure/`.
- **Reads** (list, filter, paginate, detail) go through `tasks/selectors.py`, which returns QuerySets to DRF, django-filter and DRF pagination. Visibility is the only read rule, and it's one function.
- **import-linter** contracts in CI: `tasks.domain` imports nothing from Django, DRF or Celery; `tasks.application` imports only `tasks.domain`; neither imports `tasks.infrastructure` or `tasks.api`.
- Django's own files (`models.py`, `admin.py`, `migrations/`) stay where Django expects them and count as infrastructure.

## Alternatives considered

- **Services layer only** (write functions in `services.py`, read functions in `selectors.py`, calling the ORM directly). Idiomatic and short, but rules can't be tested without a database and nothing enforces the boundaries.
- **Full ports and adapters, reads included.** The textbook version, but filtering and pagination would be rebuilt behind interfaces, adding code without protecting any rule.

## Consequences

- Domain rules and use cases are tested with in-memory fakes, no database, in milliseconds, which makes test-first development practical.
- Celery is replaceable: use cases only know the `Notifier` port.
- Some duplication: a domain `Task`, an ORM model, and the mapping between them in the repository.
- Two paths to understand. The rule of thumb: if it changes state, it's a use case; if it only reads, it's a selector.
