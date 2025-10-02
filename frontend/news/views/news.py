from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..models import CalendarEvent, News, User
from ..util.filter_objects import get_objects_with_emojis
from .utils import get_filtered_queryset, paginate_queryset


@require_GET
def news_view(request: HttpRequest) -> HttpResponse:
    """
    Ansicht für die News-Seite, die alle News anzeigt.
    """
    # Kalender
    now = timezone.now()  # Aktuelle Zeit mit Zeitzone

    if request.user.is_authenticated:
        # Eigene und globale Termine abrufen
        user_events = CalendarEvent.objects.filter(start__gte=now, user=request.user)
        global_events = CalendarEvent.objects.filter(start__gte=now, is_global=True)
        upcoming_events = (user_events | global_events).distinct().order_by("start")[:3]
    else:
        # Nur globale Termine für nicht angemeldete Benutzer
        upcoming_events = CalendarEvent.objects.filter(
            start__gte=now, is_global=True
        ).order_by("start")[:3]

    # News

    # GET-Parameter holen
    active_filters = {
        "locations": request.GET.getlist("location"),
        "categories": request.GET.getlist("category"),
        "audiences": request.GET.getlist("audience"),
        "sources": request.GET.getlist("source"),
    }

    # Hole gefilterte News basierend auf den GET-Parametern für initiale Anzeige
    news_items_queryset = get_filtered_queryset(active_filters)
    total_filtered_count = news_items_queryset.count()
    paginated_items = paginate_queryset(news_items_queryset)
    has_more = total_filtered_count > len(paginated_items)

    # Objekte, nach denen gefiltert werden kann
    objects_to_filter = get_objects_with_emojis()
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

    active_filters = {
        "locations": request.GET.getlist("location"),
        "categories": request.GET.getlist("category"),
        "audiences": request.GET.getlist("audience"),
        "sources": request.GET.getlist("source"),
    }

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
    news: News = get_object_or_404(
        News.objects.prefetch_related("texte__sprache", "quelle"), pk=pk
    )

    # Sprache aus GET-Parameter (Standard: "de")
    lang = request.GET.get("lang", "de")

    # Hole den Text für die gewählte Sprache, falls vorhanden
    text = news.texte.filter(sprache__code=lang).first()  # type: ignore[attr-defined]

    #  Objekte, nach denen gefiltert werden kann
    objects_to_filter = get_objects_with_emojis()
    locations = objects_to_filter["locations"]
    categories = objects_to_filter["categories"]
    audiences = objects_to_filter["audiences"]
    sources = objects_to_filter["sources"]

    if request.GET.get("partial") == "true":
        return render(
            request,
            "news/partials/_news_detail.html",
            {"detail_news": news, "text": text},
        )

    return render(
        request,
        "news/news.html",
        {
            "locations": locations,
            "categories": categories,
            "audiences": audiences,
            "sources": sources,
            "detail_news": news,
            "text": text,
        },
    )


@require_GET
@login_required
def foryoupage(request: HttpRequest) -> HttpResponse:
    """
    Ansicht für die For You-Seite, die personalisierte News anzeigt.
    """
    # Kalender
    now = timezone.now()

    # Eigene und globale Termine abrufen
    user_events = CalendarEvent.objects.filter(start__gte=now, user=request.user)
    global_events = CalendarEvent.objects.filter(start__gte=now, is_global=True)
    upcoming_events = (user_events | global_events).distinct().order_by("start")[:3]

    # Nutzerpräferenzen abrufen
    if isinstance(request.user, User):
        preferences = {
            "locations": list(request.user.standorte.values_list("name", flat=True)),
            "categories": list(
                request.user.inhaltskategorien.values_list("name", flat=True)
            ),
            "audiences": list(request.user.zielgruppen.values_list("name", flat=True)),
            "sources": list(request.user.quellen.values_list("name", flat=True)),
        }

        # Rundmail- und Sammel-Rundmail-Präferenzen hinzufügen
        if request.user.include_rundmail:
            preferences["sources"].append("Rundmail")
        if request.user.include_sammel_rundmail:
            preferences["sources"].append("Sammel-Rundmail")

        # News basierend auf Präferenzen filtern
        news_items_queryset = get_filtered_queryset(preferences)
        total_filtered_count = news_items_queryset.count()
        paginated_items = paginate_queryset(news_items_queryset)
        has_more = total_filtered_count > len(paginated_items)

        context = {
            "upcoming_events": upcoming_events,
            "news_list": paginated_items,
            "has_more": has_more,
        }

        return render(request, "news/foryoupage.html", context)
    else:
        messages.error(request, "Ungültiger Benutzer.")
        return redirect("login")


def links(request: HttpRequest) -> HttpResponse:
    return render(request, "news/Links.html")
