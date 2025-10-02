import json
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import connection
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate, get_language_from_path
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from icalendar import Calendar
from icalendar import Event as IcsEvent
from icalendar import vRecur

from ..forms import PreferencesForm, UserCreationForm2
from ..models import *
from ..my_logging import get_logger
from ..util.filter_objects import get_objects_with_emojis

# News


def get_filtered_queryset(active_filters: dict[str, Any]) -> QuerySet[News]:
    """
    Hilfsfunktion, die News basierend auf GET-Parametern filtert,
    absteigend sortiert.
    """
    locations = active_filters.get("locations", [])
    categories = active_filters.get("categories", [])
    audiences = active_filters.get("audiences", [])
    sources = active_filters.get("sources", [])

    queryset = News.objects.all()
    if locations:
        queryset = queryset.filter(standorte__name__in=locations)
    if categories:
        queryset = queryset.filter(inhaltskategorien__name__in=categories)
    if audiences:
        queryset = queryset.filter(zielgruppen__name__in=audiences)
    if sources:
        rundmail_types = ["Rundmail", "Sammel-Rundmail"]
        other_sources = [src for src in sources if src not in rundmail_types]
        rundmail_sources = [src for src in sources if src in rundmail_types]
        if other_sources:
            queryset = queryset.filter(quelle__name__in=other_sources)
        if rundmail_sources:
            queryset = queryset.filter(quelle_typ__in=rundmail_sources)

    return queryset.order_by("-erstellungsdatum")


def paginate_queryset(queryset: QuerySet, offset: int = 0, limit: int = 20) -> QuerySet:
    """
    Schneidet ein QuerySet entsprechend Offset und Limit.
    Standard-Werte für offset und limit kommen zum Zug, wenn die
    News-Seite neu geladen wird. Standardmäßig werden also 20
    News-Objekte an den Client gesendet, bevor JS auf dem Client
    weitere News anfordert.
    """
    return queryset[offset : offset + limit]


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


"""
User
"""


def login_view(request: HttpRequest) -> HttpResponse:
    # Hole next_url aus GET oder POST, je nach Kontext
    if request.method == "POST":
        next_url = request.POST.get(
            "next", "foryoupage"
        )  # Priorisiere POST nach Formularabsendung
    else:
        next_url = request.GET.get("next", "foryoupage")  # Initialer GET-Request

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url)  # Verwende next_url direkt
        else:
            messages.error(request, "Ungültige Anmeldedaten.")
            # Bei Fehler: next_url bleibt erhalten für das erneute Rendern

    return render(request, "news/login.html", {"next": next_url})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("News")


def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserCreationForm2(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registrierung erfolgreich! Bitte melde dich an.")
            return redirect("login")
    else:
        form = UserCreationForm2()
    return render(request, "news/register.html", {"form": form})


@login_required
def account_view(request: HttpRequest) -> HttpResponse:
    """
    Ansicht für den Account-Bereich, wo Benutzer ihr Passwort und ihren Benutzernamen ändern können.
    """
    if not request.user.is_authenticated:
        return redirect("login")
    username_error = None
    username_success = None

    if isinstance(request.user, User):
        form = PasswordChangeForm(request.user)

        if request.method == "POST":
            if "change_password" in request.POST:
                if isinstance(request.user, User):
                    form = PasswordChangeForm(request.user, request.POST)
                    old_password = form.data.get("old_password")
                    if old_password is not None and isinstance(old_password, str):
                        if not request.user.check_password(old_password):
                            # Nur diese Fehlermeldung anzeigen, alle anderen Fehler unterdrücken
                            form.errors.clear()
                            form.add_error(
                                "old_password",
                                "Das alte Passwort war falsch. Bitte neu eingeben.",
                            )
                        else:
                            if form.is_valid():
                                user = form.save()
                                update_session_auth_hash(request, user)
                                messages.success(
                                    request, "Dein Passwort wurde erfolgreich geändert!"
                                )
                                return redirect("account")

            elif "change_username" in request.POST:
                new_username = request.POST.get("new_username")
                if new_username:
                    if User.objects.filter(username=new_username).exists():
                        username_error = "Dieser Benutzername ist bereits vergeben."
                    else:
                        request.user.username = new_username
                        request.user.save()
                        username_success = "Dein Benutzername wurde geändert!"

        return render(
            request,
            "news/account.html",
            {
                "form": form,
                "username": request.user.username,
                "username_error": username_error,
                "username_success": username_success,
            },
        )

    else:
        messages.error(request, "Ungültiger Benutzer.")
        return redirect("login")


@login_required
def update_preferences(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("foryoupage")
    else:
        form = PreferencesForm(instance=request.user)
    return render(request, "news/preferences.html", {"form": form})


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


# Kalender


@login_required
def calendar_page(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "news/calendar.html",
        {"is_authenticated": request.user.is_authenticated},
    )


# REST-API für Kalender-Events


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calendar_events(request: HttpRequest) -> HttpResponse:
    # GET: Alle Events auflisten
    if request.method == "GET":
        group_param = request.GET.get("group")
        if group_param:
            # Nur Events mit diesem group-Wert zurückgeben
            events = CalendarEvent.objects.filter(group=group_param)
        elif request.user.is_authenticated:
            events = CalendarEvent.objects.filter(user=request.user)
            global_events = CalendarEvent.objects.filter(is_global=True)
            events = list(events) + list(global_events)
        else:
            events = CalendarEvent.objects.filter(is_global=True)

        event_data = [
            {
                "id": event.id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat() if event.end else None,
                "description": event.description,
                "user_id": event.user.id if event.user else None,
                "repeat": event.repeat,
                "repeat_until": (
                    event.repeat_until.isoformat() if event.repeat_until else None
                ),
                "group": event.group,
                "is_global": event.is_global,
                "hidden": False,
            }
            for event in events
        ]
        return JsonResponse(event_data, safe=False)

    # POST: Neues Event anlegen
    logger = get_logger(__name__)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Nicht authentifiziert."}, status=401)
        try:
            data = json.loads(request.body)
            title = data.get("title")
            start = data.get("start")
            end = data.get("end")
            description = data.get("description", "")
            repeat = data.get("repeat", "none")
            repeat_until_str = data.get("repeat_until")

            if not title or not start:
                return JsonResponse(
                    {"error": "Titel und Startzeit sind erforderlich."}, status=400
                )

            try:
                start_datetime = datetime.fromisoformat(start)
                start_datetime = timezone.make_aware(
                    start_datetime, timezone.get_current_timezone()
                )
            except ValueError:
                return JsonResponse(
                    {"error": "Startzeit hat ein ungültiges Format."}, status=400
                )

            now = timezone.now()

            if start_datetime < now:
                return JsonResponse(
                    {
                        "error": "Der Startzeitpunkt darf nicht in der Vergangenheit liegen."
                    },
                    status=400,
                )

            end_datetime = None
            if end:
                try:
                    end_datetime = datetime.fromisoformat(end)
                    end_datetime = timezone.make_aware(
                        end_datetime, timezone.get_current_timezone()
                    )
                except ValueError:
                    return JsonResponse(
                        {"error": "Endzeit hat ein ungültiges Format."}, status=400
                    )
                if end_datetime < start_datetime:
                    return JsonResponse(
                        {
                            "error": "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."
                        },
                        status=400,
                    )

            repeat_until = None
            if repeat_until_str:
                try:
                    repeat_until = datetime.fromisoformat(repeat_until_str)
                    repeat_until = timezone.make_aware(
                        repeat_until, timezone.get_current_timezone()
                    )
                except ValueError:
                    return JsonResponse(
                        {"error": "Wiederholungsende hat ein ungültiges Format."},
                        status=400,
                    )

            events = []
            current_start = start_datetime
            current_end = end_datetime if end_datetime else None
            group_value = title + str(now)

            if repeat != "none" and repeat_until:
                if repeat == "weekly":
                    delta = timedelta(weeks=1)
                elif repeat == "daily":
                    delta = timedelta(days=1)
                elif repeat == "monthly":
                    delta = relativedelta(months=1)
                elif repeat == "yearly":
                    delta = relativedelta(years=1)
                else:
                    delta = timedelta(days=0)

                # Verhindert, dass mehr als 50 Termine pro Serie erstellt werden
                count = 0
                temp_start = current_start
                while temp_start <= repeat_until:
                    count += 1
                    temp_start += delta
                if count > 50:
                    return JsonResponse(
                        {"error": "Maximal 50 Termine pro Serie erlaubt."}, status=400
                    )

                while current_start <= repeat_until:
                    event = CalendarEvent.objects.create(
                        user=request.user,
                        title=title,
                        start=current_start,
                        end=current_end,
                        description=description,
                        repeat=repeat,
                        repeat_until=repeat_until,
                        group=group_value,
                    )
                    events.append(event)
                    current_start += delta
                    if current_end:
                        current_end += delta
            else:
                event = CalendarEvent.objects.create(
                    user=request.user,
                    title=title,
                    start=start_datetime,
                    end=end_datetime if end_datetime else None,
                    description=description,
                    repeat=repeat,
                    repeat_until=repeat_until,
                    group=group_value,
                )
                events.append(event)

            return JsonResponse(
                {"message": "Event erfolgreich gespeichert."}, status=201
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültige JSON-Daten."}, status=400)
        except Exception as e:
            error_message = f"Fehler bei der Event-Erstellung: {str(e)}"
            logger.error(error_message)
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)


# Detail-API für einzelne Events
@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def calendar_event_detail(request: HttpRequest, event_id) -> HttpResponse:
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        # GET: Einzelnes Event anzeigen
        if request.method == "GET":
            data = {
                "id": event.id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat() if event.end else None,
                "description": event.description,
                "user_id": event.user.id if event.user else None,
                "repeat": event.repeat,
                "repeat_until": (
                    event.repeat_until.isoformat() if event.repeat_until else None
                ),
                "group": event.group,
                "is_global": event.is_global,
            }
            return JsonResponse(data)

        # PUT: Event bearbeiten
        if request.method == "PUT":
            if not request.user.is_authenticated or (
                event.user != request.user and not request.user.is_staff
            ):
                return JsonResponse({"error": "Keine Berechtigung."}, status=403)
            # Globale Events dürfen von normalen Nutzern nicht bearbeitet werden
            if event.user is None and not request.user.is_staff:
                return JsonResponse(
                    {"error": "Globale Termine können nicht bearbeitet werden."},
                    status=403,
                )
            data = json.loads(request.body)
            all_in_group = data.get("all_in_group", False)
            if all_in_group and event.group:
                events_to_update = list(
                    CalendarEvent.objects.filter(
                        group=event.group, user=event.user
                    ).order_by("start")
                )
                if not events_to_update:
                    return JsonResponse(
                        {"error": "Keine Events in der Serie gefunden."}, status=404
                    )

                # Prüfe, ob Start/Ende geändert werden sollen
                change_start = "start" in data
                change_end = "end" in data and data["end"]

                # Berechne repeat-Delta für die Serie
                repeat_value = event.repeat
                if repeat_value == "weekly":
                    repeat_delta = timedelta(weeks=1)
                elif repeat_value == "daily":
                    repeat_delta = timedelta(days=1)
                elif repeat_value == "monthly":
                    repeat_delta = relativedelta(months=1)
                elif repeat_value == "yearly":
                    repeat_delta = relativedelta(years=1)
                else:
                    repeat_delta = None

                # Neue Start-/Endzeit für den bearbeiteten Termin
                new_start_dt = None
                new_end_dt = None
                if change_start:
                    new_start_dt = datetime.fromisoformat(data["start"])
                    if timezone.is_naive(new_start_dt):
                        new_start_dt = timezone.make_aware(
                            new_start_dt, timezone.get_current_timezone()
                        )
                if change_end:
                    new_end_dt = datetime.fromisoformat(data["end"])
                    if timezone.is_naive(new_end_dt):
                        new_end_dt = timezone.make_aware(
                            new_end_dt, timezone.get_current_timezone()
                        )

                # Finde Index des bearbeiteten Events in der Serie
                ref_index = None
                for idx, ev in enumerate(events_to_update):
                    if ev.id == event.id:
                        ref_index = idx
                        break
                if ref_index is None:
                    ref_index = 0

                # Setze alle Events neu, basierend auf repeat-Delta und Referenztermin
                for idx, ev in enumerate(events_to_update):
                    # Name und Beschreibung immer aktualisieren, falls im Request
                    if "title" in data:
                        ev.title = data["title"]
                    if "description" in data:
                        ev.description = data["description"]

                    # Startzeit aktualisieren, falls gewünscht
                    if (
                        change_start
                        and repeat_delta is not None
                        and new_start_dt is not None
                    ):
                        offset = idx - ref_index
                        ev.start = new_start_dt + (repeat_delta * offset)
                    # Endzeit aktualisieren, falls gewünscht
                    if (
                        change_end
                        and repeat_delta is not None
                        and new_end_dt is not None
                    ):
                        if ev.end:
                            offset = idx - ref_index
                            ev.end = new_end_dt + (repeat_delta * offset)
                        elif not data["end"]:
                            ev.end = None
                    ev.save()

                # ...neue Logik siehe oben...
                return JsonResponse(
                    {"message": "Event-Serie erfolgreich aktualisiert."}
                )
            else:
                # Einzeltermin
                event.title = data.get("title", event.title)
                event.description = data.get("description", event.description)
                if "start" in data:
                    start_dt = datetime.fromisoformat(data["start"])
                    if timezone.is_naive(start_dt):
                        event.start = timezone.make_aware(
                            start_dt, timezone.get_current_timezone()
                        )
                    else:
                        event.start = start_dt
                if "end" in data and data["end"]:
                    end_dt = datetime.fromisoformat(data["end"])
                    if timezone.is_naive(end_dt):
                        event.end = timezone.make_aware(
                            end_dt, timezone.get_current_timezone()
                        )
                    else:
                        event.end = end_dt
                else:
                    event.end = None
                event.save()
                return JsonResponse({"message": "Event erfolgreich aktualisiert."})

        # DELETE: Event löschen
        if request.method == "DELETE":
            if not request.user.is_authenticated or (
                event.user != request.user and not request.user.is_staff
            ):
                return JsonResponse({"error": "Keine Berechtigung."}, status=403)
            all_in_group = request.GET.get("all_in_group") == "true"
            # Globale Events: Nutzer können sie nicht löschen
            if event.user is None and not request.user.is_staff:
                return JsonResponse(
                    {"error": "Globale Termine können nicht gelöscht werden."},
                    status=403,
                )
            # Normale Events löschen
            if all_in_group and event.group:
                CalendarEvent.objects.filter(
                    group=event.group, user=event.user
                ).delete()
                return JsonResponse({"success": True, "deleted_group": True})
            else:
                event.delete()
                return JsonResponse({"success": True, "deleted_group": False})

        else:
            return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)

    except Exception as e:
        return JsonResponse({"error": f"Fehler: {str(e)}"}, status=500)


@login_required
def export_ics(request: HttpRequest) -> HttpResponse:
    try:
        events = CalendarEvent.objects.filter(
            user=request.user
        ) | CalendarEvent.objects.filter(is_global=True)

        cal = Calendar()
        cal.add("prodid", "-//Mein Kalender//mxm.dk//")
        cal.add("version", "2.0")

        for event in events:
            ics_event = IcsEvent()
            ics_event.add("summary", event.title)
            ics_event.add("dtstart", event.start)
            # dtend ist optional, nur setzen wenn vorhanden und nicht None
            if getattr(event, "end", None):
                ics_event.add("dtend", event.end)
            # description ist optional
            if getattr(event, "description", None):
                ics_event.add("description", event.description)
            ics_event.add("uid", f"{event.id}@example.com")
            ics_event.add("dtstamp", timezone.now())

            # RRULE für Wiederholungen setzen
            # Add RRULE for recurring events
            if event.repeat and event.repeat != "none":
                freq_map = {
                    "daily": "DAILY",
                    "weekly": "WEEKLY",
                    "monthly": "MONTHLY",
                    "yearly": "YEARLY",
                }

                freq_value = freq_map.get(event.repeat)
                if freq_value:
                    rrule_dict: dict[str, Any] = {"FREQ": freq_value}

                    if event.repeat_until:
                        # Ensure repeat_until is a timezone-aware UTC datetime
                        until = event.repeat_until

                        if timezone.is_naive(until):
                            until = timezone.make_aware(until, dt_timezone.utc)
                        else:
                            until = until.astimezone(dt_timezone.utc)
                        # iCalendar expects UTC without tzinfo for UNTIL
                        rrule_dict["UNTIL"] = until.replace(tzinfo=None)

                    # Add the RRULE as vRecur
                    ics_event.add("rrule", vRecur(rrule_dict))

            cal.add_component(ics_event)

        ics_content = cal.to_ical()
        response = HttpResponse(ics_content, content_type="text/calendar")
        response["Content-Disposition"] = 'attachment; filename="export.ics"'
        return response

    except Exception as e:
        messages.error(request, f"Fehler beim Exportieren: {str(e)}")
        return redirect("calendar_page")


@login_required
def import_ics(request: HttpRequest) -> HttpResponse:
    if request.method == "POST" and request.FILES.get("ics_file"):
        ics_file = request.FILES["ics_file"]
        file_content = ics_file.read()

        try:
            calendar = Calendar.from_ical(file_content)
            for component in calendar.walk():
                if component.name == "VEVENT":
                    title = str(component.get("summary", "Ohne Titel"))
                    start = component.get("dtstart").dt
                    end = component.get("dtend")
                    end = end.dt if end else None
                    description = str(component.get("description", ""))

                    if isinstance(start, datetime) and not timezone.is_aware(start):
                        start = timezone.make_aware(
                            start, timezone.get_current_timezone()
                        )
                    if end and isinstance(end, datetime) and not timezone.is_aware(end):
                        end = timezone.make_aware(end, timezone.get_current_timezone())

                    # Wiederholung auslesen
                    repeat = (
                        str(component.get("rrule", {}).get("FREQ", ["none"])[0]).lower()
                        if component.get("rrule")
                        else "none"
                    )
                    repeat_until = None
                    if component.get("rrule") and "UNTIL" in component.get("rrule"):
                        until_val = component.get("rrule")["UNTIL"][0]
                        if isinstance(until_val, datetime):
                            repeat_until = until_val
                            if not timezone.is_aware(repeat_until):
                                repeat_until = timezone.make_aware(
                                    repeat_until, timezone.get_current_timezone()
                                )
                        else:
                            try:
                                repeat_until = datetime.strptime(
                                    str(until_val), "%Y%m%dT%H%M%SZ"
                                )
                                repeat_until = timezone.make_aware(
                                    repeat_until, timezone.get_current_timezone()
                                )
                            except Exception:
                                repeat_until = None

                    now = timezone.now()
                    # Format 'now' to exclude seconds and microseconds
                    now_formatted = now.strftime("%Y-%m-%d %H:%M")
                    group_value = title + now_formatted

                    # Mapping für FREQ zu delta
                    if repeat == "weekly":
                        delta = timedelta(weeks=1)
                    elif repeat == "daily":
                        delta = timedelta(days=1)
                    elif repeat == "monthly":
                        delta = relativedelta(months=1)
                    elif repeat == "yearly":
                        delta = relativedelta(years=1)
                    else:
                        delta = None

                    if repeat != "none" and repeat_until and delta:
                        current_start = start
                        current_end = end
                        while current_start <= repeat_until:
                            CalendarEvent.objects.create(
                                user=request.user,
                                title=title,
                                start=current_start,
                                end=current_end,
                                description=description,
                                repeat=repeat,
                                repeat_until=repeat_until,
                                group=group_value,
                            )
                            current_start += delta
                            if current_end:
                                current_end += delta
                    else:
                        CalendarEvent.objects.create(
                            user=request.user,
                            title=title,
                            start=start,
                            end=end,
                            description=description,
                            repeat=repeat,
                            repeat_until=repeat_until,
                            group=group_value,
                        )

            messages.success(request, "ICS-Datei erfolgreich importiert.")
        except Exception as e:
            messages.error(request, f"Fehler beim Importieren: {str(e)}")

    return redirect("calendar_page")


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


# Sprache setzen
def set_language(request):
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
