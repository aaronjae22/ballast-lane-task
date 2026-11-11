#!/bin/sh
# Apply migrations, then run the container's command (runserver, gunicorn, ...).
# The seed step (seed_demo) is added in iteration 4.
set -e

python manage.py migrate --noinput

exec "$@"
