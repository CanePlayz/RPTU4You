import os

from bs4 import BeautifulSoup
from celery import shared_task
from deep_translator import GoogleTranslator

from common.my_logging import get_logger

from .models import *
from .views.util.categorization.categorization import get_categorization_from_openai
from .views.util.translate import translate_html


@shared_task
def backfill_missing_translations():
    logger = get_logger(__name__)

    sprachen = Sprache.objects.exclude(name="Deutsch")
    news_items = News.objects.all()

    for news in news_items:
        for sprache in sprachen:
            if not Text.objects.filter(news=news, sprache=sprache).exists():
                logger.info(
                    f"Übersetze News-Objekt '{news.titel}' in {sprache.name} ({sprache.code})..."
                )

                # Übersetzung des Titels
                try:
                    translated_title = GoogleTranslator(
                        source="de", target=sprache.code
                    ).translate(news.titel)
                except Exception as e:
                    logger.error(f"Fehler bei der Übersetzung: {e}.")
                    continue
                else:
                    # Übersetzung des Textes
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
def backfill_missing_categorizations():
    logger = get_logger(__name__)

    environment = os.getenv("ENVIRONMENT", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
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
                    news.titel, german_text, environment, openai_api_key
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
