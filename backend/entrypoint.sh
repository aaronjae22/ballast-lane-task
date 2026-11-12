#!/bin/sh
# Prepare the database, then run the container's command (runserver, gunicorn, celery ...).
# Backend, worker and beat share this image, so only one of them migrates and seeds (ADR 0015):
#   MIGRATE_ON_START  migrate first unless set to something other than "true" (default: true).
#                     The worker and beat set it to false and start after the backend is healthy.
#   SEED_DEMO         run seed_demo after migrating, only when exactly "true" (default: off).
#                     Compose's backend turns it on; nothing else does.
set -e

if [ "${MIGRATE_ON_START:-true}" = "true" ]; then
    python manage.py migrate --noinput
fi

if [ "${SEED_DEMO:-false}" = "true" ]; then
    python manage.py seed_demo
fi

exec "$@"
