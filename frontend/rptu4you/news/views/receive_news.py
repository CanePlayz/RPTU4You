import gzip
import json
import os
from datetime import datetime

from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import *
from .util import translate

API_KEY = "0jdf3wfjq98w3jdf9w8"


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
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

            # Erstellungsdatum parsen
            erstellungsdatum: datetime = datetime.strptime(
                news_entry["erstellungsdatum"], "%d.%m.%Y %H:%M:%S"
            )

            # News-Objekt erstellen
            # Überprüfen, ob bereits ein News-Objekt mit diesem Titel existiert
            news_item, created = News.objects.get_or_create(
                titel=news_entry["titel"],
                defaults={
                    "link": news_entry["link"],
                    "erstellungsdatum": erstellungsdatum,
                    "quelle": quelle,
                    "quelle_typ": news_entry["quelle_typ"],
                },
            )

            # Wenn das News-Objekt neu erstellt wurde, Attribute hinzufügen
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

                # Kategorien hinzufügen
                for category in news_entry["kategorien"]:
                    if category == "Veranstaltung":
                        category_object, _ = Kategorie.objects.get_or_create(
                            name="Veranstaltung"
                        )
                    elif category == "Umfrage":
                        category_object, _ = Kategorie.objects.get_or_create(
                            name="Umfrage"
                        )
                    elif category == "Mitarbeitende":
                        category_object, _ = Kategorie.objects.get_or_create(
                            name="Mitarbeitende"
                        )
                    elif category == "Studierende":
                        category_object, _ = Kategorie.objects.get_or_create(
                            name="Studierende"
                        )
                    news_item.kategorien.add(category_object)

            # Deutschen Text speichern
            if Text.objects.filter(news=news_item, sprache__name="Deutsch").exists():
                continue
            else:
                text = Text(
                    news=news_item,
                    text=news_entry["text"],
                    titel=news_entry["titel"],
                    sprache=Sprache.objects.get(name="Deutsch"),
                )
                text.save()

        return JsonResponse({"status": "success"})
