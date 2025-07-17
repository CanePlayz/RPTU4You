import gzip
import json
import os
import re
from datetime import datetime

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from common.my_logging import get_logger

from ..models import *
from ..tasks import add_missing_translations
from .util.categorization.categorize import get_categorization_from_openai
from .util.cleanup.cleanup import get_cleaned_text_from_openai


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        logger = get_logger(__name__)
        logger.info("POST-Anfrage an /receive_news empfangen.")

        # API-Key prüfen
        api_key = os.getenv("API_KEY")
        api_key_request = request.headers.get("API-Key")
        if api_key != api_key_request:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # JSON-Daten aus dem Request-Body laden
        # Prüfe den Content-Encoding Header
        if request.headers.get("Content-Encoding") == "gzip":
            decompressed_body = gzip.decompress(request.body)
            data = json.loads(decompressed_body.decode("utf-8"))
        else:
            # Fallback, wenn nicht komprimiert
            data = json.loads(request.body.decode("utf-8"))

        # Environment überprüfen
        environment = os.getenv("ENVIRONMENT", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if environment not in ["dev", "prod"]:
            return JsonResponse(
                {"error": "Invalid environment"},
                status=400,
            )

        # News-Objekte erstellen
        for news_entry in data:

            # Quellen-Objekt erstellen
            if (
                news_entry["quelle_typ"] == "Rundmail"
                or news_entry["quelle_typ"] == "Sammel-Rundmail"
            ):
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
                quelle, _ = EmailVerteiler.objects.get_or_create(
                    name=news_entry["quelle_name"]
                )

            else:
                break

            # Erstellungsdatum parsen und sicherstellen, dass eine Zeitzone gesetzt ist
            erstellungsdatum: datetime = make_aware(
                datetime.strptime(news_entry["erstellungsdatum"], "%d.%m.%Y %H:%M:%S")
            )

            # News-Objekt erstellen
            # Überprüfen, ob bereits ein News-Objekt mit diesem Titel existiert
            logger.info(f"Verarbeite News-Eintrag: {news_entry['titel']}")
            news_item, created = News.objects.get_or_create(
                titel=news_entry["titel"],
                defaults={
                    "link": news_entry["link"],
                    "erstellungsdatum": erstellungsdatum,
                    "quelle": quelle,
                    "quelle_typ": news_entry["quelle_typ"],
                },
            )

            # Wenn das News-Objekt neu erstellt wurde, Text cleanen, Übersetzungen hinzufügen und Kategorisierung durchführen
            if created:

                # Text cleanen
                try:
                    clean_response = get_cleaned_text_from_openai(
                        news_entry["titel"],
                        news_entry["text"],
                        openai_api_key=openai_api_key,
                    )
                # Wenn ein Fehler auftritt, loggen und weitermachen mit dem nächsten Eintrag
                except Exception as e:
                    logger.error(f"Fehler beim Cleanen des Textes: {e}")

                    # Wenn der Text nicht gecleant wurde, den Originaltext speichern
                    text = Text(
                        news=news_item,
                        text=news_entry["text"],
                        titel=news_entry["titel"],
                        sprache=Sprache.objects.get(name="Deutsch"),
                    )
                    text.save()
                else:
                    logger.info("Text erfolgreich gecleant.")
                    logger.info(clean_response)

                    match_de = re.search(
                        r"\[LANGUAGE:de\]\s*\[Titel\]\s*(.*?)\s*\[Text\]\s*(.*?)\s*(?=\[LANGUAGE:|$)",
                        clean_response,
                        re.DOTALL,
                    )

                    match_en = re.search(
                        r"\[LANGUAGE:en\]\s*\[Titel\]\s*(.*?)\s*\[Text\]\s*(.*?)\s*(?=\[LANGUAGE:|$)",
                        clean_response,
                        re.DOTALL,
                    )

                    # Prüfe, ob beide Teile vorhanden sind
                    has_de = match_de is not None
                    has_en = match_en is not None

                    if not has_de or not has_en:
                        logger.error(
                            "Fehler beim Cleanen des Textes: "
                            "Es wurde nicht für beide Sprachen ein Text gefunden."
                        )
                        # Fallback: Originaltext speichern
                        text = Text(
                            news=news_item,
                            text=news_entry["text"],
                            titel=news_entry["titel"],
                            sprache=Sprache.objects.get(name="Deutsch"),
                        )
                        text.save()

                    # Extrahierte Inhalte
                    cleaned_title_de = match_de.group(1).strip() if match_de else ""
                    cleaned_text_de = match_de.group(2).strip() if match_de else ""
                    cleaned_title_en = match_en.group(1).strip() if match_en else ""
                    cleaned_text_en = match_en.group(2).strip() if match_en else ""

                    # Gecleante Texte speichern
                    text = Text(
                        news=news_item,
                        text=cleaned_text_de,
                        titel=cleaned_title_de,
                        sprache=Sprache.objects.get(name="Deutsch"),
                    )
                    text.save()
                    text = Text(
                        news=news_item,
                        text=cleaned_text_en,
                        titel=cleaned_title_en,
                        sprache=Sprache.objects.get(name="Englisch"),
                    )
                    text.save()

                    # Wenn alles erfolgreich gecleant wurde, das Flag is_cleaned_up auf True setzen
                    news_item.is_cleaned_up = True
                    news_item.save()

                    # Fehlende Übersetzungen hinzufügen
                    sprachen = Sprache.objects.all()
                    add_missing_translations(sprachen, news_item)

                # Standorte hinzufügen
                if "Kaiserslautern" in news_entry["standorte"]:
                    standort_kl, _ = Standort.objects.get_or_create(
                        name="Kaiserslautern"
                    )
                    news_item.standorte.add(standort_kl)
                if "Landau" in news_entry["standorte"]:
                    standort_ld, _ = Standort.objects.get_or_create(name="Landau")
                    news_item.standorte.add(standort_ld)

                # Inhaltskategorien und Zielgruppe(n) hinzufügen
                try:
                    categories, audiences = get_categorization_from_openai(
                        news_entry["titel"],
                        news_entry["text"],
                        environment,
                        openai_api_key,
                    )
                except Exception as e:
                    logger.error(f"Fehler bei der Kategorisierung: {e}")
                    categories, audiences = [], []
                else:
                    for category in categories:
                        category_object, _ = InhaltsKategorie.objects.get_or_create(
                            name=category
                        )
                        news_item.kategorien.add(category_object)

                    for audience in audiences:
                        audience_object, _ = Zielgruppe.objects.get_or_create(
                            name=audience
                        )
                        news_item.zielgruppe.add(audience_object)

                    logger.info("Kategorisierung erfolgreich hinzugefügt.")

                logger.info("News-Objekt erfolgreich erstellt.")

            else:
                logger.info(f"News-Objekt existiert bereits.")

        return JsonResponse({"status": "success"})
