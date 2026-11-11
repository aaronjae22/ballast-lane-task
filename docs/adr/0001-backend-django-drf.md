# ADR 0001: Django + DRF for the backend

- Status: Accepted
- Date: 2026-11-10

## Context

The brief allows Django (DRF), Flask or FastAPI. The project needs JWT auth, filtering, pagination, OpenAPI docs, rate limiting, background jobs and seeded demo data, and it's judged on architecture, tests and a live code review.

## Decision

Django 5.2 LTS with Django REST Framework.

## Alternatives considered

- **FastAPI + SQLAlchemy + Alembic.** A layered design feels more natural (dependency injection, Pydantic models, Swagger built in), but authentication, migration wiring, an admin and most integrations would be built by hand.
- **Flask.** The same trade-off as FastAPI, with fewer built-in pieces.

## Consequences

- Mature, well-known pieces cover most requirements: simplejwt, django-filter, drf-spectacular, DRF throttling, Celery integration, the admin.
- Django models combine data and persistence, so business rules have to be kept out of models, serializers and views on purpose. [ADR 0002](0002-architecture-strict-writes-plain-reads.md) covers how.
- An LTS release keeps the dependency set stable and widely supported.
