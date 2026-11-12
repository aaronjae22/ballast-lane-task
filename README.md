# ballast-lane-task

Team Task Board: a task management REST API built with Django REST Framework, with a React + TypeScript frontend. Built as a technical exercise for Ballast Lane.

> Work in progress. Setup instructions, demo credentials and an architecture overview are added as the iterations land.

## Demo credentials

`seed_demo` creates these accounts and about 25 tasks across every status and due date. The local compose stack runs it on startup (`SEED_DEMO=true`). On a host, run `uv run python manage.py seed_demo` from `backend/`. It's idempotent: a second run creates nothing.

| Username | Role | Password |
|---|---|---|
| `admin` | Admin: sees and manages every task, and can use the Django admin | `demo-password` |
| `alice` | Team member | `demo-password` |
| `bob` | Team member | `demo-password` |
| `carol` | Team member | `demo-password` |

`demo-password` is for local use only. `SEED_DEMO_PASSWORD` replaces it, and any deployment other people can reach must set it, because the seed creates a superuser ([ADR 0015](docs/adr/0015-background-jobs-and-demo-data.md)).

## Documentation

- [Specification](docs/spec.md): user story, domain rules, architecture, API, iterations
- [Architecture decision records](docs/adr/): why the main choices were made
- [AI-assisted development](docs/ai-usage.md) and the [saved prompts](docs/ai/prompts/)
- [AGENTS.md](AGENTS.md): instructions for coding agents working in this repo
