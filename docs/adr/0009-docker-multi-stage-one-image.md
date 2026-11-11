# ADR 0009: Multi-stage Docker images, one backend image for every process

- Status: Accepted
- Date: 2026-11-10

## Context

The brief requires a Dockerfile and docker-compose for the app and database. Reviewers should be able to run the full demo with one command, and production should run the same image that was tested.

## Decision

- `backend/Dockerfile` with `dev` and `prod` targets. One image runs the API, the Celery worker and Celery Beat, with different commands.
- `frontend/Dockerfile` with a `dev` target (Vite) and a `prod` target (nginx serving the build and proxying `/api`).
- `docker-compose.yml` with healthchecks, defaults that work without a `.env` file, and an entrypoint that migrates and seeds demo data.
- `docker-compose.prod.yml` runs the `prod` targets locally; CI builds both `prod` images.

## Alternatives considered

- **A separate Dockerfile per process.** More files that can drift apart.
- **Single-stage images.** Dev tools would ship to production.
- **Requiring a `.env` file before the first run.** One more setup step for every reviewer.

## Consequences

- `docker compose up --build` gives a working, seeded demo.
- The dependency layer is cached on `uv.lock`, so code changes rebuild in seconds.
- Production images are exercised locally and in CI, with or without a cloud deploy.
