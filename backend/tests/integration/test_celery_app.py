"""The Celery app and the settings it reads (ADR 0015)."""

from pathlib import Path

from celery.schedules import crontab
from django.conf import settings

from config import celery_app


def test_celery_app_is_loaded_with_django_and_named_after_the_project() -> None:
    assert celery_app.main == "config"


def test_celery_reads_its_broker_from_the_django_settings() -> None:
    assert settings.CELERY_BROKER_URL == settings.REDIS_URL
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL


def test_messages_are_json_only() -> None:
    """Jobs take ids and ISO dates, never objects, so nothing needs pickle."""
    assert settings.CELERY_TASK_SERIALIZER == "json"
    assert settings.CELERY_ACCEPT_CONTENT == ["json"]
    assert celery_app.conf.accept_content == ["json"]


def test_celery_runs_in_the_project_time_zone() -> None:
    """Beat's schedule is read in the same zone as the Clock's today (ADR 0012)."""
    assert settings.CELERY_TIMEZONE == settings.TIME_ZONE
    assert celery_app.conf.timezone == settings.TIME_ZONE


def test_results_are_not_stored_and_the_broker_is_retried_on_startup() -> None:
    """There's no result backend. The worker waits for Redis instead of exiting."""
    assert settings.CELERY_TASK_IGNORE_RESULT is True
    assert settings.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP is True


def test_an_smtp_server_that_hangs_times_out() -> None:
    """Without a timeout, one unresponsive server would hold a worker forever."""
    assert settings.EMAIL_TIMEOUT == 10


def test_beat_sends_the_due_tomorrow_reminders_daily_at_eight() -> None:
    """At 08:00 in CELERY_TIMEZONE, which is TIME_ZONE (above)."""
    entry = settings.CELERY_BEAT_SCHEDULE["due-tomorrow-reminders"]

    assert entry["task"] == "tasks.send_due_tomorrow_reminders"
    assert entry["schedule"] == crontab(hour=8, minute=0)
    assert celery_app.conf.beat_schedule == settings.CELERY_BEAT_SCHEDULE


def test_beat_keeps_its_schedule_file_out_of_the_source_folder() -> None:
    """Compose mounts backend/ into the containers: a file there would land in the repo."""
    schedule_file = Path(settings.CELERY_BEAT_SCHEDULE_FILENAME).resolve()

    assert not schedule_file.is_relative_to(settings.BASE_DIR.resolve())
    assert celery_app.conf.beat_schedule_filename == settings.CELERY_BEAT_SCHEDULE_FILENAME
