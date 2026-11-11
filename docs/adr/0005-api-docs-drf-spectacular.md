# ADR 0005: drf-spectacular instead of drf-yasg for API docs

- Status: Accepted
- Date: 2026-11-10

## Context

The brief names drf-yasg for Django projects. drf-yasg generates OpenAPI 2.0 (Swagger 2.0) only, and its own README points new projects to drf-spectacular. The frontend generates its TypeScript types from the API schema, and current generators target OpenAPI 3.

## Decision

drf-spectacular, with the schema at `/api/schema/` and Swagger UI at `/api/docs/`.

## Alternatives considered

- **drf-yasg.** Meets the brief word for word, but locks the project to OpenAPI 2.0.

## Consequences

- The same Swagger UI experience the brief asks for, generated from an OpenAPI 3 schema.
- One schema serves both the docs and the frontend's generated client.
- A conscious deviation from the brief's wording, recorded here.
