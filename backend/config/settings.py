"""Django settings, read from environment variables.

Every variable has a local default, so the app starts without a .env file.
.env.example at the repo root documents the overrides.
"""

import os
import tempfile
from datetime import timedelta
from pathlib import Path

import dj_database_url
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable: 1/true/yes/on mean True."""
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    """Read a comma-separated environment variable as a list."""
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Core

DEBUG = env_bool("DJANGO_DEBUG", default=False)

# Local development only. Refused below whenever DEBUG is off.
INSECURE_DEFAULT_SECRET_KEY = "django-insecure-local-only-do-not-use-in-production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or INSECURE_DEFAULT_SECRET_KEY
if not DEBUG and SECRET_KEY == INSECURE_DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off; "
        "the built-in default is for local development only."
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Applications

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    # Records refresh tokens, so a rotated or logged-out one is refused (ADR 0006).
    "rest_framework_simplejwt.token_blacklist",
    "accounts",
    "tasks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database. The default is the local compose database on its host port (5433);
# containers and CI set DATABASE_URL explicitly.

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default="postgres://taskboard:taskboard@localhost:5433/taskboard",
    )
}

# Cache, which the DRF throttles store their counts in. Redis everywhere it runs (compose,
# CI, production); DJANGO_CACHE=locmem is for a host without Redis. That cache lives in one
# process, so its limits don't hold across processes: never use it in production (ADR 0014).

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHE_BACKENDS = {
    "redis": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL},
    "locmem": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
_cache = os.environ.get("DJANGO_CACHE") or "redis"
if _cache not in CACHE_BACKENDS:
    raise ImproperlyConfigured(
        f"DJANGO_CACHE must be one of {', '.join(CACHE_BACKENDS)}, not {_cache!r}."
    )
CACHES = {"default": CACHE_BACKENDS[_cache]}

# Celery: Redis is the broker (ADR 0015). Jobs take ids and ISO dates, so JSON is enough;
# there's no result backend, so results are dropped. The worker waits for Redis on startup.

CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Beat: one process, one daily entry, read in CELERY_TIMEZONE. Its schedule file goes to the
# temp dir, never into backend/, which compose mounts from the repo.
CELERY_BEAT_SCHEDULE = {
    "due-tomorrow-reminders": {
        "task": "tasks.send_due_tomorrow_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
}
CELERY_BEAT_SCHEDULE_FILENAME = os.environ.get("CELERY_BEAT_SCHEDULE_FILENAME") or str(
    Path(tempfile.gettempdir()) / "taskboard-celerybeat-schedule"
)

# Email: SMTP, pointing at Mailpit locally (web UI on http://localhost:8025)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=False)
# Seconds. A hung SMTP server fails the send (and its retry) instead of holding a worker.
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Team Task Board <noreply@localhost>")

# Users and passwords

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization. Due-date rules compare against the local date, so the
# time zone is configurable; datetimes are still stored in UTC (USE_TZ).

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True
# Beat reads its schedule in the same zone as the Clock's today (ADR 0012).
CELERY_TIMEZONE = TIME_ZONE

# Django REST Framework: every endpoint requires a JWT and is throttled unless it opts out.
# JSON only: no browsable API (it can't send a JWT), and no form parsers for a cross-site
# form to post to (ADR 0014). Throttle rates are spec section 7's.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Anonymous requests count against both anon and user (by address); the stricter wins.
    # The scoped throttle applies only to views that name a throttle_scope.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min", "auth": "5/min"},
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Domain errors become HTTP here, and only here (spec section 4).
    "EXCEPTION_HANDLER": "tasks.api.exceptions.exception_handler",
}

# JWT (ADRs 0006 and 0014): a short-lived access token, kept in memory by the frontend, and
# a refresh token in an httpOnly cookie that only /api/auth/ receives. The cookie is Secure
# outside local development (DEBUG off); the override is for the prod image over plain http.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    # Every refresh issues a new refresh token, valid for another day, and refuses the old one.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/"
REFRESH_COOKIE_SECURE = env_bool("DJANGO_REFRESH_COOKIE_SECURE", default=not DEBUG)

# OpenAPI schema at /api/schema/, Swagger UI at /api/docs/ (ADRs 0005 and 0014). Both are
# public. Swagger UI is pinned rather than @latest, and persistAuthorization stays off: it
# would keep the token in localStorage.

SWAGGER_UI_DIST = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.34.1"

SPECTACULAR_SETTINGS = {
    "TITLE": "Team Task Board API",
    "DESCRIPTION": (
        "Tasks for a small team: create, assign and track them to done. To try it here, log "
        "in with POST /api/auth/token/, then paste the access token into Authorize."
    ),
    "VERSION": "0.1.0",
    "SCHEMA_PATH_PREFIX": "/api/",
    # The schema describes the API, not itself.
    "SERVE_INCLUDE_SCHEMA": False,
    # Separate request and response components, so generated types don't mark read-only
    # fields as required inputs.
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": SWAGGER_UI_DIST,
    "SWAGGER_UI_FAVICON_HREF": f"{SWAGGER_UI_DIST}/favicon-32x32.png",
}

# Logging. Django configures only its own "django" logger, so without this the project's
# loggers fall back to Python's last-resort handler, which drops everything below WARNING.
# The tasks loggers (the jobs' skipped emails among them) write INFO and up to stderr, which
# runserver, Gunicorn and Docker all show.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(levelname)s %(name)s: %(message)s"}},
    "handlers": {"stderr": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "loggers": {"tasks": {"handlers": ["stderr"], "level": "INFO"}},
}

# Static files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
