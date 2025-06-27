#!/usr/bin/env python

import os
import sys
import time

import django
import psycopg2
from psycopg2 import OperationalError

# Sicherstellen, dass die Ausgaben sofort angezeigt werden
sys.stdout.reconfigure(line_buffering=True)  # type: ignore


# Warten auf Datenbank
def wait_for_db():
    while True:
        try:
            conn = psycopg2.connect(
                dbname="mydb", user="admin", password="password", host="db"
            )
            conn.close()
            print("✓  Datenbank ist erreichbar")
            break
        except OperationalError:
            print("Warte auf Datenbank...")
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
    print("▶  Migrationen ausführen …")
    call_command("migrate", interactive=False)


# Superuser anlegen
def create_superuser():
    User = get_user_model()
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "password")

    if not User.objects.filter(username=username).exists():
        print(f"▶  Superuser '{username}' anlegen …")
        User.objects.create_superuser(username, email, password)
    else:
        print(f"✓  Superuser '{username}' existiert bereits")


# Sprachobjekte anlegen
def create_languages():
    Sprache.objects.get_or_create(name="Deutsch", code="de")
    Sprache.objects.get_or_create(name="Englisch", code="en")
    print("✓  Sprachobjekte sind vorhanden")


# Backfill-Tasks starten
def start_backfill_tasks():
    print("▶  Starte Backfill-Tasks …")
    backfill_missing_translations.delay()
    backfill_missing_categorizations.delay()


def main():
    migrate_db()
    create_superuser()
    create_languages()
    start_backfill_tasks()

    env = os.getenv("DJANGO_ENV", "development")
    if env == "production":
        # Gunicorn als neuen Prozess starten
        gunicorn_cmd = [
            "gunicorn",
            "rptu4you.wsgi:application",
            "--bind",
            "0.0.0.0:8000",
            "--workers",
            "3",
        ]
        os.execvp("gunicorn", gunicorn_cmd)  # ersetzt aktuellen Prozess
    else:
        # Entwicklungsserver ohne automatischen Reload starten
        call_command("runserver", "0.0.0.0:8000", use_reloader=False)


if __name__ == "__main__":
    main()
