# How I approached this exercise

My thought process for the Ballast Lane exercise: what I built, how I worked, the choices I made and why, and what I'd change. Setup is in the [README](README.md); how AI was used, checked and corrected is in [GENAI.md](GENAI.md).

## What I built

A Team Task Board: a Django REST Framework API with a React + TypeScript frontend, run with one `docker compose up`.

The user story ([spec section 1](docs/spec.md#1-user-story)):
- As a **team member**, I create tasks, assign them to a teammate, and track them to done.
- As an **assignee**, I see what's on my plate, what's due soon and what's overdue. I get an email when a task is assigned to me and a reminder the day before it's due.
- As an **admin**, I can see and manage every task.

Every requirement of the brief maps to where and how it's met in the [requirements traceability table](docs/spec.md#2-requirements-traceability).

## How I worked: a small software factory

Before writing any code, I read about Ballast Lane's [Software Factory](https://ballastlane.com/software-factory) and built my workflow on its ideas, at the scale of one person and one exercise. Its banner sums up the stages, Orchestrate, Build, Test and Ship, and the principle I cared most about: **human review on every decision**.

| Stage | What it was here |
|---|---|
| **Orchestrate** | Before any code, I wrote the [spec](docs/spec.md), the [ADRs](docs/adr/) and `AGENTS.md` with Claude in chat. Each iteration then got its own [prompt](docs/ai/prompts/). The builder planned every iteration in plan mode, and I reviewed each plan with Claude before approving it |
| **Build** | Claude Code, one fresh session per iteration, working from the spec, the ADRs and the prompt |
| **Test** | Failing tests first, then the code. CI on every PR: lint, architecture contracts, tests with a coverage gate, the API contract, a real-browser check, and the whole compose stack end to end |
| **Ship** | Codex reviewed every PR. I merged once CI was green and every finding was addressed |

Some of the Factory's ideas carried over directly:
- **No agent approves its own work.** Claude Code built; Codex, a model from another provider, reviewed. Neither fixed the other's findings on its own: the builder fixed what I agreed with, and I declined one false positive with evidence.
- **A different model family as the critic,** so the builder's blind spots aren't also the reviewer's.
- **A decision log.** Every choice a reviewer might question became an ADR before the code that depends on it: 18 of them.
- **Nothing counts as done until the checks pass,** and "done" in every prompt is a list of commands, not a claim.

### Human review on every decision

The agents wrote most of the code, so the risk I cared about was ending up with a codebase I couldn't explain. I wanted to check every change against the brief and the spec, and to know what was being built and why. So the agents proposed, and I decided:
- Every plan came back with its open questions and a proposed answer to each. I answered them before any code was written.
- Every commit waited for my approval before it was made.
- Every PR waited for me to merge it.

### Small commits in small PRs

This followed from the same goal. The first scaffold run produced one commit of about 1,400 lines. It worked, but I couldn't have reviewed it properly, so I set it aside and restarted with a rule written into every prompt: PRs of about 300 changed lines, each made of commits that do one thing and say why.

The result is 73 PRs and 288 commits before the final docs. A rule lands as a failing-test commit followed by the commit that makes it pass, so the history shows the TDD, and any commit can be read on its own. It's slower than letting an agent write a whole feature, but each change was small enough to understand, question and, when needed, send back.

## The order of the work

I built from the inside out, so the rules were tested before any framework touched them ([spec section 13](docs/spec.md#13-iterations)):

| Iteration | What | Why at this point |
|---|---|---|
| 0 | Tooling, Docker, CI, the Django skeleton | Every later check runs on this |
| 1 | The domain and the use cases, in plain Python | The rules are the product; they're tested first and without a database |
| 2 | The model, the repository, the read side | Persistence adapts to the domain, not the other way round |
| 3 | The API, JWT, Swagger, throttling | HTTP is a thin layer over use cases that already work |
| 4 | Celery emails, the daily reminder, the demo seed | The background jobs plug into a port the use cases already call |
| 5 | Frontend foundation: auth, routing, the generated API client | The session logic is the hardest part of the frontend, so it came first |
| 6 | Frontend features: the task screens | Built on a tested API contract |

## Design choices

Each has a short ADR with the alternatives I considered:
- **Clean Architecture where the rules are, plain Django where they aren't** ([ADR 0002](docs/adr/0002-architecture-strict-writes-plain-reads.md)). Writes go through use cases and a domain with no Django in it; import-linter enforces the boundaries in CI. Reads are ordinary querysets from one `visible_tasks(user)` selector. Layering the reads too would add code without protecting a rule.
- **Visibility as one rule** ([ADR 0003](docs/adr/0003-visibility-and-permissions.md)). Admins see everything; anyone else sees what they own or are assigned. A task you can't see is a 404, not a 403, so its existence doesn't leak.
- **Action endpoints** for start, complete, reopen and assign ([ADR 0004](docs/adr/0004-action-endpoints.md)), instead of a writable `status` field: each transition has its own permission and its own error.
- **JWT with the access token in memory and the refresh token in an httpOnly cookie**, on one origin ([ADR 0006](docs/adr/0006-jwt-refresh-cookie-same-origin.md)). JavaScript can't read the refresh token, and the same origin means no CORS.
- **drf-spectacular instead of the drf-yasg the brief names** ([ADR 0005](docs/adr/0005-api-docs-drf-spectacular.md)): drf-yasg only produces OpenAPI 2.0, and the frontend's types are generated from an OpenAPI 3 schema.
- **The email is queued after the commit** ([ADR 0015](docs/adr/0015-background-jobs-and-demo-data.md)), so a rolled-back write sends nothing and a broker outage doesn't fail a saved write.
- **React, TypeScript and Mantine** ([ADR 0007](docs/adr/0007-frontend-react-typescript-mantine.md)), with filters in the URL so a filtered list can be shared or reloaded, and no console warnings, checked in a real browser in CI ([ADR 0018](docs/adr/0018-frontend-task-screens.md)).

The [README](README.md#architecture) has the architecture diagrams.

## What I'd change on a production codebase

This workflow fits a take-home: one person, no users and no production data. On a real codebase I'd keep the principle and change the mechanics:
- **Review at the level of plans and PRs, not every commit.** Approving each commit made sure I knew every line here, but it doesn't scale. With a team, a person approves the plan and the merge, and agents work in parallel on isolated branches, as the Factory runs them.
- **A critic from another provider for the big decisions too.** Codex reviewed the code, but my plan reviews were a second Claude session, the same model family as the builder. The Factory has a critic from a different provider challenge load-bearing decisions; I'd do that for ADRs.
- **Enforce the rules, don't rely on habit.** Branch protection with a required human approval, and agents with no permission to merge.
- **More gates:** a type checker (nothing checks that the fakes match the Protocols), dependency and secret scanning, and the 100% domain coverage check as a CI job.
- **Production concerns I scoped out:** production images for both apps, migrations as their own release step instead of on every start, separate liveness and readiness checks, monitoring, and agents kept away from production data and secrets.

## What's left out

- **Production images and a deploy** (iterations 7a and 7b). The backend's `prod` image builds in CI, but there's no production compose file, nginx frontend or cloud deploy. Everything runs with the dev stack.
- **No type checker in CI**, as above.
- **Search uses `LIKE`**, with no index. [query-plans.md](docs/query-plans.md) records which indexes I'd add if the table grows.

## The demo

With the stack up ([README](README.md#run-it-with-docker)):
1. Sign in at http://localhost:5173 as `alice` / `demo-password`. She sees only her own and her assigned tasks.
2. Create a task, assign it to `bob`, then open Mailpit at http://localhost:8025: the assignment email is there.
3. Filter by status and due date, reload the page, and note the filters are still applied: they live in the URL.
4. Start and complete a task, then try to complete it again: the button is gone, and the API would answer 409.
5. Sign in as `bob`: he sees the task and can change its status, but can't edit or delete it.
6. Sign in as `admin`: every task is visible.
7. In Swagger (http://localhost:8000/api/docs/), show the same rules over HTTP.

## Where to look in the code

- The rules: [`backend/tasks/domain/`](backend/tasks/domain/), and the [permission matrix](backend/tests/unit/permission_matrix.py) that drives the tests at every level.
- A use case: [`backend/tasks/application/assign_task.py`](backend/tasks/application/assign_task.py).
- The composition root: [`backend/tasks/api/wiring.py`](backend/tasks/api/wiring.py), the one place use cases meet their adapters.
- The read side: [`backend/tasks/selectors.py`](backend/tasks/selectors.py).
- The frontend session: [`frontend/src/auth/session.ts`](frontend/src/auth/session.ts), and the races it handles in [ADR 0017](docs/adr/0017-session-concurrency-rules.md).
