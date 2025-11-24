#!/usr/bin/env python


import json
import logging
import os
import time
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple, Type

import django
import psycopg2
from news.my_logging import get_logger
from psycopg2 import OperationalError

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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify
from news.models import (
    CalendarEvent,
    EmailVerteiler,
    ExterneWebsite,
    Fachschaft,
    InhaltsKategorie,
    InterneWebsite,
    Sprache,
    Standort,
    TrustedAccountQuelle,
    Zielgruppe,
)


# Migrations durchführen
def migrate_db():
    logger.info("Führe Migrationen durch...")
    call_command("migrate", interactive=False)
    logger.info("Migrationen abgeschlossen.")


# Statische Dateien sammeln
def collect_static():
    if settings.DEBUG:
        logger.info("DEBUG aktiv, überspringe collectstatic.")
        return
    logger.info("Sammle statische Dateien...")
    call_command("collectstatic", interactive=False, verbosity=0)
    logger.info("Statische Dateien gesammelt.")


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


# Kalendereinträge aus öffentlicher Datei anlegen/aktualisieren
def _parse_event_datetime(raw_value: str, tz) -> datetime:
    parsed = parse_datetime(raw_value)
    if parsed is None:
        parsed_date = parse_date(raw_value)
        if parsed_date is None:
            raise ValueError(f"Ungültiges Datumsformat: '{raw_value}'")
        parsed = datetime.combine(parsed_date, datetime_time.min)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone=tz)
    return parsed


def create_public_calendar_events():
    logger.info("Synchronisiere öffentliche Kalendereinträge...")

    # Pfad zur Kalenderdatei bestimmen
    base_dir = Path(__file__).resolve().parent
    events_path = base_dir / "news" / "data" / "public_events.json"

    if not events_path.exists():
        logger.info(
            f"Keine öffentliche Kalenderdatei gefunden unter {events_path}. Überspringe."
        )
        return

    # Kalenderdatei lesen
    try:
        raw_data: Dict[str, Any] = json.loads(events_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error(
            f"Konnte öffentliche Kalenderdatei nicht lesen ({events_path}): {exc}"
        )
        return

    # Einträge verarbeiten
    events = raw_data.get("events", [])
    if not isinstance(events, list):
        logger.error(f"Schlüssel 'events' muss eine Liste sein ({events_path}).")
        return

    tz = timezone.get_current_timezone()

    created_count = 0
    updated_count = 0
    seen_keys: Set[Tuple[str, datetime]] = set()

    # Jeden Eintrag verarbeiten
    for item in events:
        if not isinstance(item, dict):
            logger.warning(f"Ignoriere Kalendereintrag, da er kein Objekt ist: {item}")
            continue

        # Erforderliche Felder extrahieren
        title = item.get("title")
        start_raw = item.get("start")

        # Validierung der erforderlichen Felder
        if not title or not isinstance(title, str):
            logger.warning(f"Kalendereintrag ohne gültigen Titel übersprungen: {item}")
            continue
        if not start_raw or not isinstance(start_raw, str):
            logger.warning(
                f"Kalendereintrag '{title}' ohne gültigen Startzeitpunkt übersprungen."
            )
            continue

        # Felder bereinigen
        title = title.strip()
        start_raw = start_raw.strip()
        if not title:
            logger.warning(f"Kalendereintrag ohne gültigen Titel übersprungen: {item}")
            continue
        if not start_raw:
            logger.warning(
                f"Kalendereintrag '{title}' ohne gültigen Startzeitpunkt übersprungen."
            )
            continue

        # Startzeitpunkt parsen
        try:
            start_dt = _parse_event_datetime(start_raw, tz)
        except ValueError as exc:
            logger.warning(
                f"Kalendereintrag '{title}' besitzt ungültigen Startzeitpunkt: {exc}"
            )
            continue

        dedup_key = (title.lower(), start_dt)
        # Gleiche Titel und Startzeiten werden nur einmal angelegt.
        if dedup_key in seen_keys:
            logger.warning(
                f"Doppelter Kalendereintrag für '{title}' ({start_dt}) ignoriert."
            )
            continue
        seen_keys.add(dedup_key)

        # Endzeitpunkt parsen
        end_raw = item.get("end")
        end_dt = None
        if isinstance(end_raw, str) and end_raw:
            try:
                end_dt = _parse_event_datetime(end_raw, tz)
            except ValueError as exc:
                logger.warning(
                    f"Kalendereintrag '{title}' besitzt ungültigen Endzeitpunkt: {exc}"
                )
                continue
            if end_dt < start_dt:
                logger.warning(
                    f"Kalendereintrag '{title}' übersprungen, da Endzeitpunkt vor dem Start liegt."
                )
                continue

        # Beschreibung extrahieren
        description_value = item.get("description")
        description = description_value if isinstance(description_value, str) else ""

        # All-Day-Flag extrahieren
        all_day_flag = bool(item.get("all_day"))
        if end_dt is None and (all_day_flag or len(start_raw) == 10):
            # Ganztagseinträge ohne Endzeit gehen bis zum Folgetag 00:00 Uhr
            end_dt = start_dt + timedelta(days=1)

        # Sicherstellen, dass Endzeitpunkt nach Startzeitpunkt liegt
        if end_dt and end_dt < start_dt:
            logger.warning(
                f"Kalendereintrag '{title}' übersprungen, da berechneter Endzeitpunkt vor dem Start liegt."
            )
            continue

        defaults = {
            "description": description,
            "end": end_dt,
            "user": None,
            "is_global": True,
            "repeat": "none",
            "repeat_until": None,
            "group": None,
        }

        event, is_created = CalendarEvent.objects.update_or_create(
            title=title,
            start=start_dt,
            is_global=True,
            defaults=defaults,
        )

        if is_created:
            created_count += 1
        else:
            updated_count += 1

        logger.debug(f"Kalendereintrag '{event.title}' synchronisiert (id={event.id}).")

    logger.info(
        f"Öffentliche Kalendereinträge synchronisiert: {created_count} erstellt, {updated_count} aktualisiert."
    )


# Vokabular-Daten laden
def _load_vocab_data(file_path: Path) -> Dict[str, Any]:
    """Lädt die Vokabular-Daten aus der angegebenen JSON-Datei."""
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _sync_vocab_entries(
    entries: Iterable[Dict[str, Any]],
    model: Type[Any],
) -> None:
    # Für jede Kategorie in den Daten
    for entry in entries:
        # Namen extrahieren
        names = entry.get("names") or {}
        german_name = (names.get("de") or "").strip()

        # Objekt holen oder erstellen
        if not german_name:
            continue

        slug_value = slugify(entry.get("slug") or german_name)

        # Objekt holen (mehrfacher Lookup für Resistenz)
        obj = model.objects.filter(slug=slug_value).first()
        if obj is None:
            obj = model.objects.filter(name=german_name).first()

        # Falls nötig Objekt erstellen
        was_created = obj is None
        if was_created:
            obj = model(slug=slug_value, name=german_name)

        changed = was_created

        # Slug aktualisieren
        if getattr(obj, "slug", None) != slug_value:
            obj.slug = slug_value
            changed = True

        # Namen in Deutsch aktualisieren
        if hasattr(obj, "name") and obj.name != german_name:
            obj.name = german_name
            changed = True

        # Namen in verschiedenen Sprachen aktualisieren
        for lang_code, value in names.items():
            if not isinstance(value, str):
                continue
            translated_value = value.strip()
            field_name = f"name_{lang_code}"
            if (
                hasattr(obj, field_name)
                and getattr(obj, field_name) != translated_value
            ):
                setattr(obj, field_name, translated_value)
                changed = True

        # Objekt speichern, falls nötig
        if changed:
            obj.save()


# Zuordnung für Quellenmodelle
SOURCE_MODEL_MAP: Dict[str, Type[Any]] = {
    "EmailVerteiler": EmailVerteiler,
    "Fachschaft": Fachschaft,
    "InterneWebsite": InterneWebsite,
    "ExterneWebsite": ExterneWebsite,
    "TrustedAccount": TrustedAccountQuelle,
    "TrustedAccountQuelle": TrustedAccountQuelle,
}


def _sync_source_entries(entries: Iterable[Dict[str, Any]]) -> None:
    # Für alle Einträge in den Daten
    for entry in entries:
        # Quellen-Typ extrahieren
        type_key = entry.get("type")
        if not isinstance(type_key, str):
            logger.warning(f"Quelle ohne gültigen Typ übersprungen: {entry}")
            continue

        # Passendes Modell bestimmen
        model = SOURCE_MODEL_MAP.get(type_key)
        if model is None:
            logger.warning(f"Unbekannter Quellentyp '{type_key}' übersprungen.")
            continue

        # Namen extrahieren
        names = entry.get("names") or {}
        if not isinstance(names, dict):
            logger.warning(f"Quelle ohne gültige Namensstruktur übersprungen: {entry}")
            continue
        german_name = (names.get("de") or "").strip()
        if not german_name:
            logger.warning(f"Quelle ohne deutschen Namen übersprungen: {entry}")
            continue

        slug_value = slugify(entry.get("slug") or german_name)

        # URL extrahieren
        raw_url = entry.get("url")
        url = None
        if isinstance(raw_url, str):
            url = raw_url.strip() or None

        # Objekt holen (mehrfacher Lookup für Resistenz)
        obj = model.objects.filter(slug=slug_value).first()
        if obj is None and url is not None:
            obj = model.objects.filter(url=url).first()
        if obj is None:
            obj = model.objects.filter(name=german_name).first()

        # Falls nötig Objekt erstellen
        was_created = obj is None
        if was_created:
            obj = model(slug=slug_value)

        changed = was_created

        # Slug aktualisieren
        if getattr(obj, "slug", None) != slug_value:
            obj.slug = slug_value
            changed = True

        # Namen in Deutsch aktualisieren
        if hasattr(obj, "name") and obj.name != german_name:
            obj.name = german_name
            changed = True

        # URL aktualisieren
        if obj.url != url:
            obj.url = url
            changed = True

        # Namen in verschiedenen Sprachen aktualisieren
        for lang_code, value in names.items():
            if not isinstance(value, str):
                continue
            translated_value = value.strip()
            field_name = f"name_{lang_code}"
            if (
                hasattr(obj, field_name)
                and getattr(obj, field_name) != translated_value
            ):
                setattr(obj, field_name, translated_value)
                changed = True

        # Objekt speichern, falls nötig
        if changed:
            obj.save()


# Datenbank-Elemente für Kategorien anlegen
def create_category_translations():
    logger.info("Erstelle Kategorien-Objekte in verschiedenen Sprachen...")
    data_file = Path(__file__).resolve().parent / "news" / "data" / "categories.json"
    data = _load_vocab_data(data_file)

    with transaction.atomic():
        for label, key, model in (
            ("Inhaltskategorie", "content_categories", InhaltsKategorie),
            ("Zielgruppe", "audience_categories", Zielgruppe),
            ("Standort", "location_categories", Standort),
        ):
            _sync_vocab_entries(data.get(key, []), model)

    logger.info("Kategorien-Objekte erstellt.")


# Datenbank-Elemente für Quellen anlegen
def create_sources():
    logger.info("Synchronisiere Quellen...")
    data_file = Path(__file__).resolve().parent / "news" / "data" / "categories.json"
    data = _load_vocab_data(data_file)

    source_entries: list = data.get("sources", [])

    with transaction.atomic():
        _sync_source_entries(source_entries)

    logger.info("Quellen-Objekte erstellt.")


# Unerwünschte Logger deaktivieren
def disable_unwanted_loggers():
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    migrate_db()
    collect_static()
    create_superuser()
    create_languages()
    create_public_calendar_events()
    create_category_translations()
    create_sources()
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
            "6",
        ]
        os.execvp("gunicorn", gunicorn_cmd)  # ersetzt aktuellen Prozess
    elif server == "django":
        logger.info("Starte Django Entwicklungsserver...")
        # Entwicklungsserver ohne automatischen Reload starten
        call_command("runserver", "0.0.0.0:8000", use_reloader=False)


if __name__ == "__main__":
    main()
