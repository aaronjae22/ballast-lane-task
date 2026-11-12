"""Celery application (ADR 0015).

Started with: celery -A config worker (and celery -A config beat).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# Celery options come from Django settings prefixed with CELERY_ (e.g. CELERY_BROKER_URL).
app.config_from_object("django.conf:settings", namespace="CELERY")
# The jobs live in tasks/infrastructure/jobs.py (spec section 4), not in a tasks.py per app,
# which is where Celery looks by default.
app.autodiscover_tasks(["tasks.infrastructure"], related_name="jobs")
