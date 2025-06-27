import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rptu4you.settings")

app = Celery("rptu4you")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "backfill_translations": {
        "task": "news.tasks.backfill_missing_translations",
        "schedule": timedelta(hours=1),
    },
    "backfill_categorizations": {
        "task": "news.tasks.backfill_missing_categorizations",
        "schedule": timedelta(hours=1),
    },
}
