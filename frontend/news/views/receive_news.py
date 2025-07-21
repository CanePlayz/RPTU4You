import gzip
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import *
from ..my_logging import get_logger
from ..tasks import add_audiences_and_categories, add_missing_translations
from ..util.close_db_connection import close_db_connection
from .util.categorization.categorize import get_categorization_from_openai
from .util.cleanup.cleanup import extract_parts, get_cleaned_text_from_openai


@close_db_connection
def process_news_entry(news_entry, openai_api_key, environment, logger: logging.Logger):
    logger.info(f"Verarbeite News-Eintrag | {news_entry["titel"][:80]}")

    # Quellen-Objekt erstellen
    if news_entry["quelle_typ"] in [
        "Rundmail",
        "Sammel-Rundmail",
        "Stellenangebote Sammel-Rundmail",
    ]:
        rundmail_id = news_entry["rundmail_id"]
        # Nachschauen, ob bereits ein Quelle-Objekt mit dieser ID existiert, falls nicht, dann erstellen
        quelle, created = Rundmail.objects.get_or_create(
            name=news_entry["quelle_name"],
            defaults={
                "rundmail_id": rundmail_id,
            },
        )

        # Wenn das Quelle-Objekt neu erstellt wurde, die URL setzen
        if created:
            if news_entry["quelle_typ"] == "Rundmail":
                quelle.url = news_entry["link"]
            elif news_entry["quelle_typ"] == "Sammel-Rundmail":
                quelle.url = news_entry["link"].split("#")[0]
            elif news_entry["quelle_typ"] == "Stellenangebote Sammel-Rundmail":
                quelle.url = news_entry["link"].split("#")[0]
            quelle.save()

    elif news_entry["quelle_typ"] == "Interne Website":
        quelle, _ = InterneWebsite.objects.get_or_create(
            name=news_entry["quelle_name"],
            defaults={
                "url": "https://rptu.de/newsroom",
            },
        )

    elif news_entry["quelle_typ"] == "Fachschaft":
        quelle, _ = Fachschaft.objects.get_or_create(
            name=news_entry["quelle_name"],
            defaults={
                "url": "https://wiwi.rptu.de/aktuelles/aktuelles-und-mitteilungen",
            },
        )

    elif news_entry["quelle_typ"] == "Email-Verteiler":
        quelle, _ = EmailVerteiler.objects.get_or_create(name=news_entry["quelle_name"])

    else:
        logger.warning("Unbekannter Quellentyp, Eintrag wird übersprungen")
        return

    # Erstellungsdatum parsen und sicherstellen, dass eine Zeitzone gesetzt ist
    erstellungsdatum: datetime = make_aware(
        datetime.strptime(news_entry["erstellungsdatum"], "%d.%m.%Y %H:%M:%S")
    )

    # News-Objekt erstellen
    # Überprüfen, ob bereits ein News-Objekt mit diesem Titel existiert
    news_item, created = News.objects.get_or_create(
        titel=news_entry["titel"],
        erstellungsdatum=erstellungsdatum,
        defaults={
            "link": news_entry["link"],
            "quelle": quelle,
            "quelle_typ": news_entry["quelle_typ"],
        },
    )

    # Wenn das News-Objekt neu erstellt wurde, Text cleanen, Übersetzungen hinzufügen und Kategorisierung durchführen
    if not created:
        logger.info(f"News-Objekt existiert bereits | {news_entry["titel"][:80]}")
        return

    # Text cleanen
    try:
        clean_response = get_cleaned_text_from_openai(
            news_entry["titel"],
            news_entry["text"],
            openai_api_key,
            24000000,  # Token-Limit für die Verarbeitung neuer News (diese sollen schnell erscheinen)
        )
        parts = extract_parts(clean_response)

    # Wenn ein Fehler auftritt, loggen und weitermachen mit dem nächsten Eintrag
    except Exception as e:
        logger.error(f"Fehler beim Cleanup: {e} | {news_entry["titel"][:80]}")

        # Fallback: Originaltext speichern
        text_object = Text(
            news=news_item,
            text=news_entry["text"],
            titel=news_entry["titel"],
            sprache=Sprache.objects.get(name="Deutsch"),
        )
        text_object.save()

    else:
        # Gecleante Texte speichern
        text_object = Text(
            news=news_item,
            text=parts["cleaned_text_de"],
            titel=parts["cleaned_title_de"],
            sprache=Sprache.objects.get(name="Deutsch"),
        )
        text_object.save()

        text_object = Text(
            news=news_item,
            text=parts["cleaned_text_en"],
            titel=parts["cleaned_title_en"],
            sprache=Sprache.objects.get(name="Englisch"),
        )
        text_object.save()

        # Flag is_cleaned_up auf True setzen
        news_item.is_cleaned_up = True
        news_item.save()
        logger.info(f"Text erfolgreich gecleant | {news_entry["titel"][:80]}")

        # Fehlende Übersetzungen hinzufügen
        sprachen = Sprache.objects.all()
        add_missing_translations(sprachen, news_item, openai_api_key, 2400000)

    # Standorte hinzufügen
    for ort in news_entry["standorte"]:
        standort_obj, _ = Standort.objects.get_or_create(name=ort)
        news_item.standorte.add(standort_obj)

    # Inhaltskategorien und Zielgruppe(n) hinzufügen
    try:
        categories, audiences = get_categorization_from_openai(
            news_entry["titel"],
            news_entry["text"],
            environment,
            openai_api_key,
            2400000,  # Token-Limit für die Verarbeitung neuer News (diese sollen schnell erscheinen)
        )
    except Exception as e:
        logger.error(f"Fehler bei Kategorisierung: {e} | {news_entry["titel"][:80]}")
        categories, audiences = [], []

    add_audiences_and_categories(news_item, categories, audiences)

    logger.info(f"Kategorisierung erfolgreich hinzugefügt | {news_entry["titel"][:80]}")

    logger.info(f"News-Objekt erfolgreich erstellt | {news_entry["titel"][:80]}")


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        logger = get_logger(__name__)
        logger.info("POST-Anfrage an /receive_news empfangen.")

        # API-Key überprüfen
        api_key = os.getenv("API_KEY")
        api_key_request = request.headers.get("API-Key")
        if api_key != api_key_request:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # Daten aus der Anfrage extrahieren
        if request.headers.get("Content-Encoding") == "gzip":
            decompressed_body = gzip.decompress(request.body)
            data = json.loads(decompressed_body.decode("utf-8"))
        else:
            data = json.loads(request.body.decode("utf-8"))

        # Environment und OpenAI-API-Key aus den Environment-Variablen lesen
        environment = os.getenv("ENVIRONMENT", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if environment not in ["dev", "prod"]:
            return JsonResponse({"error": "Invalid environment"}, status=400)

        # News parallel verarbeiten
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    process_news_entry, entry, openai_api_key, environment, logger
                )
                for entry in data
            ]
            for future in as_completed(futures):
                future.result()

        return JsonResponse({"status": "success"})
