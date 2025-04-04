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
        data = json.loads(request.body)

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
                    rundmail_id=rundmail_id,
                    defaults={
                        "rundmail_id": rundmail_id,
                    },
                )

                # Wenn das Quelle-Objekt neu erstellt wurde, die URL und den Namen setzen
                if created:
                    quelle.name = news_entry["quelle_name"]
                    if news_entry["quelle_typ"] == "Rundmail":
                        quelle.url = news_entry["link"]
                    elif news_entry["quelle_typ"] == "Sammel-Rundmail":
                        quelle.url = news_entry["link"].split("#")[0]
                    quelle.save()

            if news_entry["quelle_typ"] == "Interne Website":
                quelle, _ = InterneWebsite.objects.get_or_create(
                    name=news_entry["quelle_name"],
                    defaults={
                        "name": news_entry["quelle_name"],
                        "url": "https://rptu.de/newsroom",
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
                    sprache=Sprache.objects.get(name="Deutsch"),
                    text=news_entry["text"],
                )
                text.save()

            # Übersetzungen prüfen und ggf. erstellen
            languages = Sprache.objects.exclude(name="Deutsch")
            for sprache in languages:
                lang = sprache.name
                code = sprache.code

                # Prüfen, ob die Übersetzung bereits existiert
                text = Text.objects.filter(news=news_item, sprache__name=lang)
                if text.exists():
                    # Übersetzung existiert bereits, daher überspringen
                    continue
                else:
                    try:
                        soup = BeautifulSoup(news_entry["text"], "html.parser")
                        translate.translate_html(soup, from_lang="de", to_lang=code)
                        translated_text = str(soup)
                        text = Text(
                            news=news_item,
                            sprache=Sprache.objects.get(name=lang),
                            text=translated_text,
                        )
                        text.save()
                    except Exception as e:
                        print(f"Fehler bei der Übersetzung für {lang}: {e}")

        return JsonResponse({"status": "success"})
