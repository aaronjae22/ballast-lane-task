# ADR 0010: AI-assisted workflow with separate builder and reviewer

- Status: Accepted
- Date: 2026-11-10

## Context

The brief asks for the prompt used to generate the scaffold or implementation, a sample of the output, and how the output was validated and corrected. The evaluation looks for fluency with AI tools and critical thinking about their output.

## Decision

- **Roles.** Claude (chat) helped draft the spec and these ADRs. Claude Code builds, with one fresh session per iteration working from `AGENTS.md` and the spec. Codex reviews every pull request, a different model family, and never pushes fixes. I approve every decision and review tests before implementation.
- **Provenance.** Prompts are saved in `docs/ai/prompts/`. Agents commit at checkpoints, every `git commit` waits for my approval, and agent commits carry a `Co-Authored-By` trailer that Claude Code adds through `.claude/settings.json`. My corrections are separate commits without it. The same file denies Claude Code push, merge and history rewrites. Pull requests are merged with merge commits.
- **Scope of the headline prompt.** Prompt 01 generates the scaffold, not the full implementation. Later iterations use smaller, test-first prompts.

## Alternatives considered

- **One prompt for the full implementation.** Fast, but it skips test-first development and produces more code than can be reviewed carefully.
- **One agent writing and reviewing its own work.** Shares its own blind spots.
- **Agents never commit; I commit their output.** Also puts a person on every commit, but the AI-versus-human split would depend on me labeling commits by hand. Approving each agent commit gives the same review point with labels added automatically.
- **Squash merges.** A cleaner history, but they erase the difference between AI output and human corrections.

## Consequences

- A reviewable trail from prompt to output to correction.
- More pull requests and commits, and slower than letting one agent run end to end, by design.
