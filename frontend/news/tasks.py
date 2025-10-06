import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

from celery import shared_task
from django.db.models import QuerySet
from django.utils.timezone import now

from .models import *
from .my_logging import get_logger
from .util.close_db_connection import close_db_connection
from .views.util.categorization.categorize import get_categorization_from_openai
from .views.util.cleanup.cleanup import extract_parts, get_cleaned_text_from_openai
from .views.util.translation.translate import translate_html


def add_missing_translations(
    sprachen: QuerySet[Sprache], news: News, openai_api_key: str, token_limit: int
):
    logger = get_logger(__name__)

    for sprache in sprachen:
        if not Text.objects.filter(news=news, sprache=sprache).exists():
            logger.info(
                f"Übersetzung für {sprache.name} ({sprache.code}) hinzufügen | {news.titel[:80]}"
            )

            try:
                text_object_en = Text.objects.get(news=news, sprache__name="Englisch")
                translated_title, translated_text = translate_html(
                    text_object_en.titel,
                    text_object_en.text,
                    sprache,
                    openai_api_key,
                    token_limit,
                )
            except Exception as e:
                logger.error(
                    f"Fehler beim Übersetzen des Textes: {e} | {news.titel[:80]}"
                )
            else:
                # Neues Text-Objekt für die übersetzte Sprache erstellen
                Text.objects.get_or_create(
                    news=news,
                    sprache=sprache,
                    defaults={
                        "titel": translated_title,
                        "text": translated_text,
                    },
                )
                logger.info(
                    f"Übersetzung für {sprache.name} erfolgreich hinzugefügt | {news.titel[:80]}"
                )


def add_audiences_and_categories(
    news: News,
    categories: list[str],
    audiences: list[str],
):
    # Erlaube nur vordefinierte Kategorien und Zielgruppen
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    content_categories_file_path = os.path.join(
        BASE_DIR, "views", "util", "categorization", "inhaltskategorien.txt"
    )
    target_group_categories_file_path = os.path.join(
        BASE_DIR, "publikumskategorien.txt"
    )
    with open(
        content_categories_file_path,
        "r",
        encoding="utf-8",
    ) as file:
        allowed_categories = file.read().strip().split("\n")
    with open(
        target_group_categories_file_path,
        "r",
        encoding="utf-8",
    ) as file:
        allowed_audiences = file.read().strip().split("\n")

    # Nur erlaubte Kategorien und Zielgruppen hinzufügen
    for category in categories:
        if category in allowed_categories:
            category_object, _ = InhaltsKategorie.objects.get_or_create(name=category)
            news.inhaltskategorien.add(category_object)

    for audience in audiences:
        if audience in allowed_audiences:
            audience_object, _ = Zielgruppe.objects.get_or_create(name=audience)
            news.zielgruppen.add(audience_object)


# Einzelne Verarbeitungsschritte für News-Objekte zur Parallelisierung


@close_db_connection
def process_translation(
    news: News, sprachen, openai_api_key, token_limit, logger: logging.Logger
):
    if news.is_cleaned_up:
        add_missing_translations(sprachen, news, openai_api_key, token_limit)
    else:
        logger.info(
            f"Überspringe Übersetzungen, Objekt noch nicht gecleant | {news.titel[:80]}"
        )


@close_db_connection
def process_categorization(
    news: News, environment, openai_api_key, token_limit, logger: logging.Logger
):
    if not news.inhaltskategorien.exists():
        logger.info(f"Füge Kategorisierungen hinzu | {news.titel[:80]}")
        try:
            german_text = Text.objects.get(news=news, sprache__name="Deutsch").text
        except Text.DoesNotExist:
            return
        try:
            categories, audiences = get_categorization_from_openai(
                news.titel, german_text, environment, openai_api_key, token_limit
            )
        except Exception as e:
            logger.error(f"Fehler bei Kategorisierung: {e} | {news.titel[:80]}")
        else:
            add_audiences_and_categories(news, categories, audiences)

            logger.info(f"Kategorisierung erfolgreich hinzugefügt | {news.titel[:80]}")


@close_db_connection
def process_cleanup(news: News, openai_api_key, token_limit, logger: logging.Logger):
    if not news.is_cleaned_up:
        logger.info(f"Führe Cleanup durch | {news.titel[:80]}")
        try:
            german_text = Text.objects.get(news=news, sprache__name="Deutsch").text
        except Text.DoesNotExist:
            return
        try:
            clean_response = get_cleaned_text_from_openai(
                news.titel, german_text, openai_api_key, token_limit
            )
            parts = extract_parts(clean_response)
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e} | {news.titel[:80]}")
            return
        else:
            # Bisheriges deutsches Text-Objekt aktualisieren
            text_object = Text.objects.get(news=news, sprache__name="Deutsch")
            text_object.text = parts["cleaned_text_de"]
            text_object.titel = parts["cleaned_title_de"]
            text_object.save()

            # Neues Text-Objekt für Englisch erstellen
            Text.objects.create(
                news=news,
                text=parts["cleaned_text_en"],
                titel=parts["cleaned_title_en"],
                sprache=Sprache.objects.get(name="Englisch"),
            )

            # Flag is_cleaned_up auf True setzen
            news.is_cleaned_up = True
            news.save()
            logger.info("Cleanup erfolgreich durchgeführt | {news.titel[:80]}")


# Backfill-Tasks mit Parallelisierung


@shared_task
def backfill_missing_translations():
    logger = get_logger(__name__)
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    token_limit = 2000000  # Token-Limit von 2.000.000, da Backfill-Tasks alter News keine höhere Priorität haben

    sprachen = Sprache.objects.all()

    # Nur News-Objekte, die älter als 5 Minuten sind, werden berücksichtigt
    cutoff_time = now() - timedelta(minutes=5)
    news_items = News.objects.filter(created_at__lte=cutoff_time)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                process_translation, news, sprachen, openai_api_key, token_limit, logger
            )
            for news in news_items
        ]
        for future in as_completed(futures):
            future.result()


@shared_task
def backfill_missing_categorizations():
    logger = get_logger(__name__)

    environment = os.getenv("ENVIRONMENT", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    token_limit = 2000000  # Token-Limit von 2.000.000, da Backfill-Tasks alter News keine höhere Priorität haben

    # Nur News-Objekte, die älter als 5 Minuten sind, werden berücksichtigt
    cutoff_time = now() - timedelta(minutes=5)
    news_items = News.objects.filter(created_at__lte=cutoff_time)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                process_categorization,
                news,
                environment,
                openai_api_key,
                token_limit,
                logger,
            )
            for news in news_items
        ]
        for future in as_completed(futures):
            future.result()


@shared_task
def backfill_cleanup():
    logger = get_logger(__name__)

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    token_limit = 2000000  # Token-Limit von 2.000.000, da Backfill-Tasks alter News keine höhere Priorität haben

    # Nur News-Objekte, die älter als 5 Minuten sind, werden berücksichtigt
    cutoff_time = now() - timedelta(minutes=5)
    news_items = News.objects.filter(created_at__lte=cutoff_time)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_cleanup, news, openai_api_key, token_limit, logger)
            for news in news_items
        ]
        for future in as_completed(futures):
            future.result()
