from typing import Any, List

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..forms import PreferencesForm
from ..models import CalendarEvent, News, User
from ..services.news_filters import (
    FilterParams,
    get_filtered_queryset,
    get_objects_with_metadata,
    paginate_queryset,
)


def _build_active_filters(request: HttpRequest) -> FilterParams:
    """Aktive Filter aus den GET-Parametern extrahieren."""
    return {
        "locations": request.GET.getlist("location"),
        "categories": request.GET.getlist("category"),
        "audiences": request.GET.getlist("audience"),
        "sources": request.GET.getlist("source"),
    }


def _get_upcoming_events(request: HttpRequest) -> List[CalendarEvent]:
    """Gibt die kommenden Kalenderereignisse zurück."""
    now = timezone.now()

    if request.user.is_authenticated:
        user_events = CalendarEvent.objects.filter(start__gte=now, user=request.user)
        global_events = CalendarEvent.objects.filter(start__gte=now, is_global=True)
        return list((user_events | global_events).distinct().order_by("start")[:4])

    return list(
        CalendarEvent.objects.filter(start__gte=now, is_global=True).order_by("start")[
            :4
        ]
    )


def _build_user_preferences(user: User) -> FilterParams:
    """Erstellt die Filterpräferenzen basierend auf den Benutzereinstellungen."""
    preferences: dict[str, List[str]] = {
        "locations": [],
        "categories": [],
        "audiences": [],
        "sources": [],
    }

    # Alle verfügbaren Filterobjekte laden
    filter_items = get_objects_with_metadata()

    def _identifier_set(items: List[dict[str, Any]]) -> set[str]:
        return {
            str(item["identifier"])
            for item in items
            if item.get("identifier") is not None
        }

    # Listen der Identifier für jeden Filtertyp erstellen
    location_identifiers = _identifier_set(filter_items["locations"])
    category_identifiers = _identifier_set(filter_items["categories"])
    audience_identifiers = _identifier_set(filter_items["audiences"])
    source_identifiers = _identifier_set(filter_items["sources"])

    # Präferenzen basierend auf Benutzereinstellungen füllen
    for location in user.standorte.all():
        slug = getattr(location, "slug", None)
        if (
            slug
            and slug in location_identifiers
            and slug not in preferences["locations"]
        ):
            preferences["locations"].append(slug)

    for category in user.inhaltskategorien.all():
        slug = getattr(category, "slug", None)
        if (
            slug
            and slug in category_identifiers
            and slug not in preferences["categories"]
        ):
            preferences["categories"].append(slug)

    for audience in user.zielgruppen.all():
        slug = getattr(audience, "slug", None)
        if (
            slug
            and slug in audience_identifiers
            and slug not in preferences["audiences"]
        ):
            preferences["audiences"].append(slug)

    for source in user.quellen.all():
        slug = getattr(source, "slug", None)
        if slug and slug in source_identifiers and slug not in preferences["sources"]:
            preferences["sources"].append(slug)

    if user.include_rundmail and "rundmail" in source_identifiers:
        if "rundmail" not in preferences["sources"]:
            preferences["sources"].append("rundmail")
    if user.include_sammel_rundmail and "sammel_rundmail" in source_identifiers:
        if "sammel_rundmail" not in preferences["sources"]:
            preferences["sources"].append("sammel_rundmail")

    return preferences


@require_GET
def news_view(request: HttpRequest) -> HttpResponse:
    """
    Ansicht für die News-Seite, die alle News anzeigt.
    """
    upcoming_events = _get_upcoming_events(request)
    active_filters = _build_active_filters(request)

    # Hole gefilterte News basierend auf den GET-Parametern für initiale Anzeige
    news_items_queryset = get_filtered_queryset(active_filters)
    total_filtered_count = news_items_queryset.count()
    paginated_items = paginate_queryset(news_items_queryset)
    has_more = total_filtered_count > len(paginated_items)

    # Objekte, nach denen gefiltert werden kann
    objects_to_filter = get_objects_with_metadata()
    locations = objects_to_filter["locations"]
    categories = objects_to_filter["categories"]
    audiences = objects_to_filter["audiences"]
    sources = objects_to_filter["sources"]

    context = {
        "upcoming_events": upcoming_events,
        "news_list": paginated_items,
        "locations": locations,
        "categories": categories,
        "audiences": audiences,
        "sources": sources,
        "active_filters": active_filters,
        "has_more": has_more,
    }

    return render(request, "news/news.html", context)


@require_GET
def news_partial(request: HttpRequest) -> HttpResponse:
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 20))

    active_filters = _build_active_filters(request)

    # Hole gefilterte News basierend auf den GET-Parametern
    news_items_queryset = get_filtered_queryset(active_filters)
    total_filtered_count = news_items_queryset.count()
    paginated_items = paginate_queryset(news_items_queryset, offset, limit)
    has_more = total_filtered_count > (offset + limit)

    return render(
        request,
        "news/partials/_news_list.html",
        {"news_list": paginated_items, "has_more": has_more},
    )


@require_GET
def news_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Partielles Laden von News-Details oder bei Direktaufruf die komplette News-Seite mit Details."""
    news: News = get_object_or_404(
        News.objects.prefetch_related("texte__sprache", "quelle"), pk=pk
    )

    # Sprache aus Django-Einstellungen holen
    lang = getattr(request, "LANGUAGE_CODE", "")

    # Hole den Text für die gewählte Sprache, falls vorhanden
    text = news.texte.filter(sprache__code=lang).first()  # type: ignore[attr-defined]

    if request.GET.get("partial") == "true":
        return render(
            request,
            "news/partials/_news_detail.html",
            {"news": news, "text": text},
        )

    # Kommende Kalenderereignisse für die Seitenleiste
    upcoming_events = _get_upcoming_events(request)

    #  Objekte, nach denen gefiltert werden kann
    objects_to_filter = get_objects_with_metadata()
    locations = objects_to_filter["locations"]
    categories = objects_to_filter["categories"]
    audiences = objects_to_filter["audiences"]
    sources = objects_to_filter["sources"]

    return render(
        request,
        "news/news.html",
        {
            "locations": locations,
            "categories": categories,
            "audiences": audiences,
            "sources": sources,
            "detail_news": news,
            "upcoming_events": upcoming_events,
            "text": text,
        },
    )


@require_GET
@login_required
def foryoupage(request: HttpRequest) -> HttpResponse:
    """
    Ansicht für die For You-Seite, die personalisierte News anzeigt.
    """
    upcoming_events = _get_upcoming_events(request)
    user = request.user

    if not isinstance(user, User):
        return redirect("login")

    preferences = _build_user_preferences(user)
    news_items_queryset = get_filtered_queryset(preferences)
    total_filtered_count = news_items_queryset.count()
    paginated_items = paginate_queryset(news_items_queryset)
    has_more = total_filtered_count > len(paginated_items)

    context = {
        "upcoming_events": upcoming_events,
        "news_list": paginated_items,
        "has_more": has_more,
        "preferences_form": PreferencesForm(instance=user),
    }

    return render(request, "news/foryoupage.html", context)


@require_GET
@login_required
def foryoupage_partial(request: HttpRequest) -> HttpResponse:
    user = request.user

    if not isinstance(user, User):
        return HttpResponse(status=400)

    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 20))

    preferences = _build_user_preferences(user)
    news_items_queryset = get_filtered_queryset(preferences)
    total_filtered_count = news_items_queryset.count()
    paginated_items = paginate_queryset(news_items_queryset, offset, limit)
    has_more = total_filtered_count > (offset + limit)

    return render(
        request,
        "news/partials/_news_list.html",
        {"news_list": paginated_items, "has_more": has_more},
    )


def links(request: HttpRequest) -> HttpResponse:
    return render(request, "news/links.html")
