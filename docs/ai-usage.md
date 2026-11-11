# AI-assisted development

How generative AI was used to build this project, answering the GenAI section of the brief. The workflow is described in `docs/spec.md` section 12 and [ADR 0010](adr/0010-ai-workflow-builder-reviewer.md).

> In progress. Each section is filled in as the iterations land.

## Tools and roles

| Role | Tool |
|---|---|
| Planning and architecture | Claude (chat) |
| Builder | Claude Code in VS Code |
| Reviewer | Codex code review on GitHub pull requests |
| Decision-maker | Me |

## The prompt

The headline prompt is [`ai/prompts/01-scaffold.md`](ai/prompts/01-scaffold.md), which generates the API scaffold. Every later iteration has its own prompt in [`ai/prompts/`](ai/prompts/).

## The output

_A representative sample of the generated code, with links to the agent's commits._

Every commit an agent made carries a `Co-Authored-By` trailer; my corrections don't. To list commits with their co-authors:

```bash
git log --format='%h  %<(48,trunc)%s  %(trailers:key=Co-Authored-By,valueonly,separator=%x2C )'
```

## How I validated the AI's suggestions

_Tests written first, coverage gate, import-linter, ruff, Codex reviews, manual review checklist._

## What I corrected or improved

| # | Iteration | What the AI produced | Problem | Fix | Commit |
|---|---|---|---|---|---|

## Edge cases, authentication and validation

_How each was specified, tested and checked in the generated code._

## Performance and idiomatic quality

_Query counts, indexes, `EXPLAIN` results, and the Django/DRF idiom review._

## What I'd do differently
