from django.conf import settings

from config import celery_app


def test_celery_app_is_loaded_with_django_and_named_after_the_project() -> None:
    assert celery_app.main == "config"


def test_celery_reads_its_broker_from_the_django_settings() -> None:
    assert settings.CELERY_BROKER_URL == settings.REDIS_URL
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL
