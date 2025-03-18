import json
from datetime import datetime
from pydoc import text

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import News, Quelle, Standort

API_KEY = "0jdf3wfjq98w3jdf9w8"


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        api_key = request.headers.get("API-Key")
        if api_key != API_KEY:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        # News-Objekte erstellen
        for news_entry in data:
            # Quelle erstellen
            if (
                news_entry["quelle_typ"] == "Rundmail"
                or news_entry["quelle_typ"] == "Sammel-Rundmail"
            ):
                quelle_id = news_entry["quelle_id"]
                # Nachschauen, ob bereits ein Quelle-Objekt mit dieser ID existiert
                quelle, created = Quelle.objects.get_or_create(
                    rundmail_id=quelle_id,
                    defaults={
                        "rundmail_id": quelle_id,
                    },
                )
                if created:
                    quelle.name = news_entry["quelle_name"]
                    if news_entry["quelle_typ"] == "Rundmail":
                        quelle.url = news_entry["link"]
                    elif news_entry["quelle_typ"] == "Sammel-Rundmail":
                        quelle.url = news_entry["link"].split("#")[0]

            erstellungsdatum = datetime.strptime(
                news_entry["erstellungsdatum"], "%Y-%m-%d %H:%M:%S"
            ).date()

            news_item = News.objects.create(
                link=news_entry["link"],
                titel=news_entry["titel"],
                erstellungsdatum=erstellungsdatum,
                text=news_entry["text"],
                quelle=quelle,
                quelle_typ=news_entry["quelle_typ"],
            )

            # Standorte hinzufügen
            if "Kaiserslautern" in news_entry["standorte"]:
                standort_kl = Standort.objects.get(name="Kaiserslautern")
                news_item.standorte.add(standort_kl)

        return JsonResponse({"status": "success", "news_id": news_item.pk})
