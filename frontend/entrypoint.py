#!/usr/bin/env python


import logging
import os
import time
from typing import cast

import django
import psycopg2
from celery.app.task import Task
from psycopg2 import OperationalError

from common.my_logging import get_logger

logger = get_logger(__name__)


# Warten auf Datenbank
def wait_for_db():
    while True:
        try:
            conn = psycopg2.connect(
                dbname="mydb", user="admin", password="password", host="db"
            )
            conn.close()
            logger.info("Datenbank ist erreichbar.")
            break
        except OperationalError:
            logger.warning("Datenbank ist noch nicht erreichbar, warte...")
            time.sleep(1)


wait_for_db()

# Django initialisieren
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rptu4you.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from news.models import Sprache
from news.tasks import backfill_missing_categorizations, backfill_missing_translations


# Migrations durchführen
def migrate_db():
    logger.info("Führe Migrationen durch...")
    call_command("migrate", interactive=False)
    logger.info("Migrationen abgeschlossen.")


# Superuser anlegen
def create_superuser():
    logger.info("Überprüfe, ob Superuser existiert...")
    User = get_user_model()
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "password")

    if not User.objects.filter(username=username).exists():
        logger.info("Erstelle Superuser...")
        User.objects.create_superuser(username, email, password)
        logger.info("Superuser erfolgreich erstellt.")
    else:
        logger.info("Superuser existiert bereits.")


# Sprachobjekte anlegen
def create_languages():
    logger.info("Überprüfe, ob Sprachobjekte existieren...")
    Sprache.objects.get_or_create(name="Deutsch", name_englisch="German", code="de")
    Sprache.objects.get_or_create(name="Englisch", name_englisch="English", code="en")
    Sprache.objects.get_or_create(name="Französisch", name_englisch="French", code="fr")
    Sprache.objects.get_or_create(name="Spanisch", name_englisch="Spanish", code="es")
    logger.info("Sprachobjekte sind vorhanden.")


# Backfill-Tasks starten
def start_backfill_tasks():
    logger.info("Starte Backfill-Tasks...")
    # Cast für den Type-Checker, da der ansonsten nicht checkt, dass die Funktionen Tasks sind
    cast(Task, backfill_missing_translations).delay()
    cast(Task, backfill_missing_categorizations).delay()
    logger.info("Backfill-Tasks gestartet.")


# Unerwünschte Logger deaktivieren
def disable_unwanted_loggers():
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    migrate_db()
    create_superuser()
    create_languages()
    # start_backfill_tasks()
    disable_unwanted_loggers()

    server = os.getenv("SERVER", "development")
    if server == "gunicorn":
        # Gunicorn als neuen Prozess starten
        logger.info("Starte Gunicorn...")
        gunicorn_cmd = [
            "gunicorn",
            "rptu4you.wsgi:application",
            "--bind",
            "0.0.0.0:8000",
            "--workers",
            "3",
        ]
        os.execvp("gunicorn", gunicorn_cmd)  # ersetzt aktuellen Prozess
    elif server == "django":
        logger.info("Starte Django Entwicklungsserver...")
        # Entwicklungsserver ohne automatischen Reload starten
        call_command("runserver", "0.0.0.0:8000", use_reloader=False)


if __name__ == "__main__":
    main()
