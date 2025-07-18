import gzip
import json
import os
from datetime import datetime

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from common.my_logging import get_logger

from ..models import *
from .util.categorization.categorization import get_categorization_from_openai


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

            # Wenn das News-Objekt neu erstellt wurde, Attribute und Übersetzungen hinzufügen
            if created:

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

                # Deutschen Text speichern
                if Text.objects.filter(
                    news=news_item, sprache__name="Deutsch"
                ).exists():
                    continue
                else:
                    text = Text(
                        news=news_item,
                        text=news_entry["text"],
                        titel=news_entry["titel"],
                        sprache=Sprache.objects.get(name="Deutsch"),
                    )
                    text.save()

                # Übersetzungen hinzufügen

                logger.info("News-Objekt erfolgreich erstellt.")

            else:
                logger.info(f"News-Objekt existiert bereits.")

        return JsonResponse({"status": "success"})
