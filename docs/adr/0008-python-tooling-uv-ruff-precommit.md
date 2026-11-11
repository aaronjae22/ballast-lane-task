# ADR 0008: uv, ruff and pre-commit with local hooks

- Status: Accepted
- Date: 2026-11-10

## Context

The brief asks for a `pyproject.toml` with poetry or uv, pre-commit, and other good practices.

## Decision

- **uv** manages the Python version, the virtual environment and `uv.lock` (committed), with a dev dependency group.
- **ruff** for linting and formatting; **import-linter** for the architecture contracts; **pytest-cov** with `fail_under = 80`.
- **pre-commit** with local hooks that run `uv run ...`, so the editor, pre-commit and CI use exactly the versions in `uv.lock`.
- Committed `.vscode/settings.json` and `extensions.json` with project behavior only (interpreter, formatters, test discovery), no personal appearance settings.

## Alternatives considered

- **poetry.** Works well; uv is faster and also installs and pins the Python version.
- **black + isort + flake8.** Three tools and three configs where ruff does it all.
- **Pinned remote pre-commit hooks.** The hook's ruff version can drift from the one in the virtual environment, so the editor and the commit disagree.

## Consequences

- One config file (`pyproject.toml`) for dependencies and tool settings.
- Contributors need uv installed, or they can use Docker only.
