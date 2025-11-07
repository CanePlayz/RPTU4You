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
def process_news_entry(news_entry, openai_api_key, logger: logging.Logger):
    TOKEN_LIMIT = 2_400_000

    raw_title = news_entry.get("titel")
    truncated_title = raw_title[:80] if isinstance(raw_title, str) else "<unbekannt>"
    logger.info(f"Verarbeite News-Eintrag | {truncated_title}")

    manual_categories = news_entry.get("manual_inhaltskategorien", [])
    manual_audiences = news_entry.get("manual_zielgruppen", [])

    # Quellen-Objekt erstellen
    if news_entry["quelle_typ"] in [
        "Rundmail",
        "Sammel-Rundmail",
        "Stellenangebote Sammel-Rundmail",
    ]:
        rundmail_id = news_entry.get("rundmail_id")
        if rundmail_id is None:
            logger.warning(
                f"Rundmail ohne rundmail_id, Eintrag wird übersprungen | {truncated_title}"
            )
            return
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

    elif news_entry["quelle_typ"] == "Trusted Account":
        quelle, created = TrustedAccountQuelle.objects.get_or_create(
            name=news_entry["quelle_name"],
            defaults={"url": None},
        )

    else:
        logger.warning("Unbekannter Quellentyp, Eintrag wird übersprungen")
        return

    # Erstellungsdatum parsen und sicherstellen, dass eine Zeitzone gesetzt ist
    try:
        erstellungsdatum: datetime = make_aware(
            datetime.strptime(news_entry["erstellungsdatum"], "%d.%m.%Y %H:%M:%S")
        )
    except ValueError:
        logger.error(
            f"Erstellungsdatum ungültig, Eintrag wird übersprungen | {truncated_title}"
        )
        return

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
        logger.info(f"News-Objekt existiert bereits | {truncated_title}")
        return

    # Text cleanen
    try:
        clean_response = get_cleaned_text_from_openai(
            news_entry["titel"],
            news_entry["text"],
            openai_api_key,
            TOKEN_LIMIT,  # Token-Limit für die Verarbeitung neuer News (diese sollen schnell erscheinen)
        )
        parts = extract_parts(clean_response)

    # Wenn ein Fehler auftritt, loggen und weitermachen mit dem nächsten Eintrag
    except Exception as e:
        logger.error(f"Fehler beim Cleanup: {e} | {truncated_title}")

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
        logger.info(f"Text erfolgreich gecleant | {truncated_title}")

        # Fehlende Übersetzungen hinzufügen
        add_missing_translations(
            Sprache.objects.all(), news_item, openai_api_key, TOKEN_LIMIT
        )

    # Standorte hinzufügen
    for ort in news_entry["standorte"]:
        standort_obj, _ = Standort.objects.get_or_create(name=ort)
        news_item.standorte.add(standort_obj)

    # Inhaltskategorien und Zielgruppe(n) hinzufügen
    categories, audiences = [], []
    try:
        categories, audiences = get_categorization_from_openai(
            news_entry["titel"],
            news_entry["text"],
            openai_api_key,
            TOKEN_LIMIT,  # Token-Limit für die Verarbeitung neuer News (diese sollen schnell erscheinen)
        )
        logger.info(f"Kategorisierung erfolgreich hinzugefügt | {truncated_title}")
    except Exception as e:
        logger.error(f"Fehler bei Kategorisierung: {e} | {truncated_title}")
    finally:
        # Kombination aus automatisch ermittelten und von Trusted Accounts gegebenen Kategorien/Zielgruppen
        combined_categories = list(dict.fromkeys([*categories, *manual_categories]))
        combined_audiences = list(dict.fromkeys([*audiences, *manual_audiences]))
        add_audiences_and_categories(news_item, combined_categories, combined_audiences)

    logger.info(f"News-Objekt erfolgreich erstellt | {truncated_title}")


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        logger = get_logger(__name__)
        logger.info("POST-Anfrage an /receive_news empfangen.")

        # API-Key überprüfen
        api_key = os.getenv("API_KEY")
        if not api_key:
            logger.error("API_KEY ist nicht gesetzt.")
            return JsonResponse({"error": "Server misconfigured"}, status=500)
        api_key_request = request.headers.get("API-Key")
        if api_key != api_key_request:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # Daten aus der Anfrage extrahieren
        try:
            if request.headers.get("Content-Encoding") == "gzip":
                decompressed_body = gzip.decompress(request.body)
                data = json.loads(decompressed_body.decode("utf-8"))
            else:
                data = json.loads(request.body.decode("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ungültige Anfrage, konnte Payload nicht parsen: %s", exc)
            return JsonResponse({"error": "Invalid payload"}, status=400)

        if not isinstance(data, list):
            logger.warning("Ungültige Anfrage, Payload ist kein Array")
            return JsonResponse({"error": "Payload must be a list"}, status=400)

        # OpenAI-API-Key aus den Environment-Variablen lesen
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY ist nicht gesetzt.")
            return JsonResponse({"error": "Server misconfigured"}, status=500)

        # News parallel verarbeiten
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_news_entry, entry, openai_api_key, logger)
                for entry in data
            ]
            for future in as_completed(futures):
                future.result()

        return JsonResponse({"status": "success"})
