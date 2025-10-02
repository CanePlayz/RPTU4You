import os
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from django.db import connection
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils.translation import activate, get_language_from_path

from ..models import News


def request_date(request: HttpRequest) -> HttpResponse:
    # API-Key prüfen
    api_key = os.getenv("API_KEY")
    api_key_request = request.headers.get("API-Key")
    if api_key != api_key_request:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    # Aktuelles Datum der neuesten News abrufen
    try:
        # Hole das neueste News-Objekt
        latest_news = News.objects.filter(
            quelle_typ__in=["Sammel-Rundmail", "Rundmail"]
        ).latest("erstellungsdatum")
    except News.DoesNotExist:
        # Wenn keine News-Objekte vorhanden sind, gib eine Fehlermeldung zurück
        return JsonResponse({"error": "No news available"}, status=404)

    date: datetime = latest_news.erstellungsdatum

    return JsonResponse({"date": date.strftime("%d.%m.%Y %H:%M:%S")})


def db_connection_status(request: HttpRequest) -> HttpResponse:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database();"
        )
        result = cursor.fetchone()
        count = result[0] if result is not None else 0
    return JsonResponse({"active_db_connections": count})


def health_check(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"status": "ok"}, status=200)


def set_language(request: HttpRequest) -> HttpResponse:
    language = request.GET.get("language", "de")  # Default: German
    activate(language)
    request.session["django_language"] = language

    # Parse the current URL
    current_url = request.META.get("HTTP_REFERER", "/")
    parsed_url = urlparse(current_url)

    # Replace the language prefix in the path
    path = parsed_url.path
    current_language = get_language_from_path(path)
    if current_language:
        path = path.replace(f"/{current_language}/", f"/{language}/", 1)
    else:
        path = f"/{language}{path}" if not path.startswith(f"/{language}") else path

    # Rebuild the URL with the updated path
    updated_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )

    return HttpResponseRedirect(updated_url)
