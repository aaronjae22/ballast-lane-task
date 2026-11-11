"""Celery application. Tasks arrive in iteration 4; the app is defined now.

Started with: celery -A config worker (and celery -A config beat).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# Celery options come from Django settings prefixed with CELERY_ (e.g. CELERY_BROKER_URL).
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
