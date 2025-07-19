import logging.config
import os
from datetime import timedelta

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rptu4you.settings")

app = Celery("rptu4you")

# Nötig, damit Celery nicht seine eigene Logging-Konfiguration verwendet
app.log.setup = lambda *args, **kwargs: None

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Nutze die Django-Logging-Konfiguration auch für Celery
logging.config.dictConfig(settings.LOGGING)


""" app.conf.beat_schedule = {
    "backfill_translations": {
        "task": "news.tasks.backfill_missing_translations",
        "schedule": timedelta(hours=1),
    },
    "backfill_categorizations": {
        "task": "news.tasks.backfill_missing_categorizations",
        "schedule": timedelta(hours=1),
    },
} """

app.conf.beat_schedule = {
    "backfill_translations": {
        "task": "news.tasks.backfill_missing_translations",
        "schedule": timedelta(minutes=1),
    },
    "backfill_categorizations": {
        "task": "news.tasks.backfill_missing_categorizations",
        "schedule": timedelta(minutes=1),
    },
    "backfill_cleanup": {
        "task": "news.tasks.backfill_cleanup",
        "schedule": timedelta(minutes=1),
    },
}
