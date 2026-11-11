# syntax=docker/dockerfile:1

# One image for every backend process (API now; Celery worker and beat later),
# with dev and prod targets (spec section 10, ADR 0009).

FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

# The venv lives outside /app so the dev source mount doesn't hide it.
# uv uses the image's Python instead of downloading one; packages are
# byte-compiled at install time, and copied (not hard-linked) from the cache mount.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime dependencies only. This layer rebuilds only when the lock changes.
FROM base AS deps

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Local development: adds the dev group; compose mounts the source over /app.
FROM deps AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production: no dev dependencies, static files collected, non-root user.
FROM deps AS prod

COPY . .

# Settings refuse the built-in key with DEBUG off; collectstatic needs no real secret.
RUN DJANGO_SECRET_KEY=build-only-collectstatic python manage.py collectstatic --noinput

RUN groupadd --system --gid 10001 app \
    && useradd --system --no-log-init --uid 10001 --gid app --no-create-home app
# Numeric, so runtimes can verify the user is non-root without reading /etc/passwd.
USER 10001:10001

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
