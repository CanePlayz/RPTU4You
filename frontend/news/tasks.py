import os
import token

from bs4 import BeautifulSoup
from celery import shared_task
from deep_translator import GoogleTranslator
from django.db.models import QuerySet

from common.my_logging import get_logger

from .models import *
from .views.util.categorization.categorize import get_categorization_from_openai
from .views.util.cleanup.cleanup import extract_parts, get_cleaned_text_from_openai
from .views.util.translation.translate import translate_html


def add_missing_translations(sprachen: QuerySet[Sprache], news: News):
    logger = get_logger(__name__)

    for sprache in sprachen:
        if not Text.objects.filter(news=news, sprache=sprache).exists():
            logger.info(
                f"Übersetze News-Objekt '{news.titel}' in {sprache.name} ({sprache.code})..."
            )

            # Übersetzung des Titels (immer vom Originaltitel aus)
            try:
                translated_title = GoogleTranslator(
                    source="de", target=sprache.code
                ).translate(news.titel)
            except Exception as e:
                logger.error(f"Fehler bei der Übersetzung: {e}.")
                continue
            else:
                # Übersetzung des Textes (präfiert von Englisch, falls nicht vorhanden von Deutsch)
                try:
                    original_text_en = Text.objects.get(
                        news=news, sprache__name="Englisch"
                    ).text
                    soup = BeautifulSoup(original_text_en, "html.parser")
                    translate_html(soup, from_lang="en", to_lang=sprache.code)
                    Text.objects.create(
                        news=news,
                        text=str(soup),
                        titel=translated_title,
                        sprache=sprache,
                    )
                except Exception as e:
                    try:
                        original_text_de = Text.objects.get(
                            news=news, sprache__name="Deutsch"
                        ).text
                        soup = BeautifulSoup(original_text_de, "html.parser")
                        translate_html(soup, from_lang="de", to_lang=sprache.code)
                        Text.objects.create(
                            news=news,
                            text=str(soup),
                            titel=translated_title,
                            sprache=sprache,
                        )
                    except Exception as e:
                        logger.error(f"Fehler bei der Übersetzung: {e}.")
                        continue
                else:
                    logger.info("Übersetzung erfolgreich erstellt.")


@shared_task
def backfill_missing_translations():
    logger = get_logger(__name__)

    sprachen = Sprache.objects.all()
    news_items = News.objects.all()

    for news in news_items:
        if news.is_cleaned_up:
            logger.info(
                f"Füge fehlende Übersetzungen für News-Objekt '{news.titel}' hinzu..."
            )
            add_missing_translations(sprachen, news)
        else:
            logger.info(
                f"News-Objekt '{news.titel}' ist noch nicht gecleant. Überspringe Übersetzungen."
            )


@shared_task
def backfill_missing_categorizations():
    logger = get_logger(__name__)

    environment = os.getenv("ENVIRONMENT", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    token_limit = 2000000  # Token-Limit von 2.000.000, da Backfill-Tasks alter News keine höhere Priorität haben

    news_items = News.objects.all()
    for news in news_items:
        if not news.kategorien.exists():
            logger.info(
                f"Füge Kategorisierungen für News-Objekt '{news.titel}' hinzu..."
            )
            try:
                german_text = Text.objects.get(news=news, sprache__name="Deutsch").text
            except Text.DoesNotExist:
                logger.warning(
                    f"Kein deutscher Text gefunden. Überspringe Kategorisierung."
                )
                continue
            try:
                categories, audiences = get_categorization_from_openai(
                    news.titel, german_text, environment, openai_api_key, token_limit
                )
            except Exception as e:
                logger.error(f"Fehler bei der Kategorisierung: {e}")
                continue
            else:
                for category in categories:
                    category_object, _ = InhaltsKategorie.objects.get_or_create(
                        name=category
                    )
                    news.kategorien.add(category_object)

                for audience in audiences:
                    audience_object, _ = Zielgruppe.objects.get_or_create(name=audience)
                    news.zielgruppe.add(audience_object)

                logger.info("Kategorisierungen erfolgreich hinzugefügt.")


@shared_task
def backfill_cleanup():
    logger = get_logger(__name__)

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    token_limit = 2000000  # Token-Limit von 2.000.000, da Backfill-Tasks alter News keine höhere Priorität haben

    news_items = News.objects.all()
    for news in news_items:
        if not news.is_cleaned_up:
            logger.info(f"Führe Cleanup für News-Objekt '{news.titel}' durch...")
            try:
                german_text = Text.objects.get(news=news, sprache__name="Deutsch").text
            except Text.DoesNotExist:
                logger.warning(f"Kein deutscher Text gefunden. Überspringe Cleanup.")
                continue
            try:
                clean_response = get_cleaned_text_from_openai(
                    news.titel, german_text, openai_api_key, token_limit
                )
            except Exception as e:
                logger.error(f"Fehler beim Cleanup: {e}")
                continue
            else:
                # Wenn eine Antwort von OpenAI erhalten wurde, die Teile extrahieren
                try:
                    parts = extract_parts(clean_response)
                # Der Fehler tritt auf, wenn die Antwort nicht das erwartete Format hat
                except Exception as e:
                    logger.error(f"Fehler beim Extrahieren der Teile: {e}")
                    continue

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

                logger.info("Cleanup erfolgreich durchgeführt.")
