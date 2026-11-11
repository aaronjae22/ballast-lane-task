# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Start each iteration in plan mode. Read `AGENTS.md`, `docs/spec.md` and `docs/adr/`, then propose a plan (files to create or change, tests first, commands to run) and wait for approval before editing.
- One session per iteration. The repo is the memory: anything that matters later belongs in code, tests, the spec, an ADR or `AGENTS.md`, not in the conversation.
- Before saying you're done, run the checks in `AGENTS.md` that apply and include their results in your summary.
