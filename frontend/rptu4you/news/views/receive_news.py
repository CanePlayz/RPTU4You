import json
import os
from datetime import datetime
from pydoc import text

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import Kategorie, News, Rundmail, Standort

API_KEY = "0jdf3wfjq98w3jdf9w8"


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        api_key = os.getenv("API_KEY")
        api_key_request = request.headers.get("API-Key")
        if api_key != api_key_request:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        # News-Objekte erstellen
        for news_entry in data:
            # Quelle erstellen
            if (
                news_entry["quelle_typ"] == "Rundmail"
                or news_entry["quelle_typ"] == "Sammel-Rundmail"
            ):
                quelle_id = news_entry["rundmail_id"]
                # Nachschauen, ob bereits ein Quelle-Objekt mit dieser ID existiert
                rundmail, created = Rundmail.objects.get_or_create(
                    rundmail_id=quelle_id,
                    defaults={
                        "rundmail_id": quelle_id,
                    },
                )
                if created:
                    rundmail.name = news_entry["quelle_name"]
                    if news_entry["quelle_typ"] == "Rundmail":
                        rundmail.url = news_entry["link"]
                    elif news_entry["quelle_typ"] == "Sammel-Rundmail":
                        rundmail.url = news_entry["link"].split("#")[0]
                    rundmail.save()

            erstellungsdatum = datetime.strptime(
                news_entry["erstellungsdatum"], "%d.%m.%Y %H:%M:%S"
            ).date()

            # News-Objekt erstellen
            # Überprüfen, ob bereits ein News-Objekt mit diesem Titel existiert
            existing_news = News.objects.filter(titel=news_entry["titel"]).first()
            if not existing_news:
                news_item = News.objects.create(
                    link=news_entry["link"],
                    titel=news_entry["titel"],
                    erstellungsdatum=erstellungsdatum,
                    text=news_entry["text"],
                    quelle=rundmail,
                    quelle_typ=news_entry["quelle_typ"],
                )

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

        return JsonResponse({"status": "success"})
