import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import News

API_KEY = ""


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveNews(View):
    def post(self, request):
        api_key = request.headers.get("API-Key")
        if api_key != API_KEY:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)
        news_item = News.objects.create(
            link=data["link"],
            titel=data["titel"],
            erstellungsdatum=data["erstellungsdatum"],
            quelle_id=data["quelle_id"],
            quelle_typ=data["quelle_typ"],
            stellenangebot=data["stellenangebot"],
            uni_info=data["uni_info"],
            event=data["event"],
            externe_news=data["externe_news"],
            umfragen=data["umfragen"],
        )
        return JsonResponse({"status": "success", "news_id": news_item.pk})
