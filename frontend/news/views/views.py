import json
import os
import traceback
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from icalendar import Calendar

from common.my_logging import get_logger

from ..forms import PreferencesForm, UserCreationForm2
from ..models import *

# News
# Info: news_view unten, bis jetzt nur Kalender auf der rechten Seite eingebunden. Jacob fragen ob man daraus zwei Views machen kann oder nicht
# Allgemine zentrale News-API, die News basierend auf verschiedenen Eingabe-Parametern zurückgibt:
# - Gefiltert nach Benutzerpräferenzen in Bezug auf Inhalt, Standort usw.
# - Mit einem Offset


# Präferenzen werden sowohl bei direktem Aufruf der Website mit Filtern als auch bei JS-Anfragen immer in URL encoded und damit immer gleich verarbeitet


# JS lädt auch aus dieser API die News, wenn die Seite geladen wird
@csrf_exempt
@require_GET
def news_api(request):
    """
    Zentrale News-API:
    - Filtert News nach GET-Parametern (kategorie, standort, zielgruppe, offset, limit)
    - Berücksichtigt bei eingeloggten Nutzern automatisch deren Präferenzen, falls keine Filter gesetzt sind
    - Gibt News als JSON zurück
    """
    kategorie_ids = request.GET.getlist("kategorie")
    standort_ids = request.GET.getlist("standort")
    zielgruppe_ids = request.GET.getlist("zielgruppe")
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 10))

    news_qs = News.objects.all().order_by("-erstellungsdatum")

    # Wenn keine Filter gesetzt und User eingeloggt: User-Präferenzen verwenden
    if request.user.is_authenticated and not (
        kategorie_ids or standort_ids or zielgruppe_ids
    ):
        if hasattr(request.user, "präferenzen") and request.user.präferenzen.exists():
            kategorie_ids = [str(k.id) for k in request.user.präferenzen.all()]
        if hasattr(request.user, "standorte") and request.user.standorte.exists():
            standort_ids = [str(s.id) for s in request.user.standorte.all()]
        if hasattr(request.user, "zielgruppe") and request.user.zielgruppe.exists():
            zielgruppe_ids = [str(z.id) for z in request.user.zielgruppe.all()]

    if kategorie_ids:
        news_qs = news_qs.filter(kategorien__id__in=kategorie_ids)
    if standort_ids:
        news_qs = news_qs.filter(standorte__id__in=standort_ids)
    if zielgruppe_ids:
        news_qs = news_qs.filter(zielgruppe__id__in=zielgruppe_ids)

    news_qs = news_qs.distinct()[offset : offset + limit]

    news_data = [
        {
            "id": n.id,
            "titel": n.titel,
            "text": n.text,
            "erstellungsdatum": n.erstellungsdatum.strftime("%d.%m.%Y %H:%M:%S"),
            "link": n.link,
            "quelle_typ": n.quelle_typ,
        }
        for n in news_qs
    ]

    return JsonResponse({"news": news_data, "count": news_qs.count()})


def news_detail(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    return render(request, "news/detail.html", {"news": news_item})


def Links(request):
    return render(request, "news/Links.html")


"""
ANMELDUNG
"""


def login_view(request):
    # Hole next_url aus GET oder POST, je nach Kontext
    if request.method == "POST":
        next_url = request.POST.get(
            "next", "ForYouPage"
        )  # Priorisiere POST nach Formularabsendung
    else:
        next_url = request.GET.get("next", "ForYouPage")  # Initialer GET-Request

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


def logout_view(request):
    logout(request)
    return redirect("News")


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm2(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registrierung erfolgreich! Bitte melde dich an.")
            return redirect("login")
    else:
        form = UserCreationForm2()
    return render(request, "news/register.html", {"form": form})


def ForYouPage(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Die For You-Seite ist nur mit Anmeldung einsehbar.")
        return redirect("login")
    else:
        return render(request, "news/ForYouPage.html")


@login_required
def account_view(request):
    """
    Ansicht für den Account-Bereich, wo Benutzer ihr Passwort und ihren Benutzernamen ändern können.
    """
    form = PasswordChangeForm(request.user)  # Formular initialisieren

    if request.method == "POST":
        if "change_password" in request.POST:
            # Neues Passwort-Formular mit POST-Daten erstellen
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                # Formular speichern und Benutzer aktualisieren
                user = form.save()
                # Session nach Passwortänderung aktualisieren, damit der Benutzer angemeldet bleibt
                update_session_auth_hash(request, user)
                messages.success(request, "Dein Passwort wurde erfolgreich geändert!")
                return redirect("account")
            else:
                messages.error(request, "Bitte korrigiere die Fehler unten.")

        elif "change_username" in request.POST:
            # Neuen Benutzernamen aus dem Formular holen
            new_username = request.POST.get("new_username")
            if new_username:
                if User.objects.filter(username=new_username).exists():
                    messages.error(request, "Dieser Benutzername ist bereits vergeben.")
                else:
                    request.user.username = new_username
                    request.user.save()
                    messages.success(request, "Dein Benutzername wurde geändert!")
                return redirect("account")

    # Rendern der Account-Seite mit dem Formular und dem aktuellen Benutzernamen
    return render(
        request, "news/account.html", {"form": form, "username": request.user.username}
    )


@login_required
def update_preferences(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("ForYouPage")
    else:
        form = PreferencesForm(instance=request.user)
    return render(request, "news/preferences.html", {"form": form})


def request_date(request):
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


# Alternative mit Nachricht für nicht angemeldete Benutzer


"""
KALENDER
"""


@login_required
def calendar_page(request):
    return render(
        request,
        "news/calendar.html",
        {"is_authenticated": request.user.is_authenticated},
    )


# Kalenderanzeige auf Latest News Seite
def news_view(request):
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

    context = {
        "upcoming_events": upcoming_events,
    }
    return render(request, "news/News.html", context)


# REST-API für Kalender-Events


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calendar_events(request):
    # GET: Alle Events auflisten
    if request.method == "GET":
        if request.user.is_authenticated:
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
                "hidden": False,  # Optionally, can be set True if needed
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
def calendar_event_detail(request, event_id):
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
                # Neues Start/Ende vom User
                new_start = None
                new_end = None
                if "start" in data:
                    new_start_dt = datetime.fromisoformat(data["start"])
                    if timezone.is_naive(new_start_dt):
                        new_start = timezone.make_aware(
                            new_start_dt,
                            timezone.get_current_timezone(),
                        )
                    else:
                        new_start = new_start_dt
                if "end" in data and data["end"]:
                    new_end_dt = datetime.fromisoformat(data["end"])
                    if timezone.is_naive(new_end_dt):
                        new_end = timezone.make_aware(
                            new_end_dt,
                            timezone.get_current_timezone(),
                        )
                    else:
                        new_end = new_end_dt
                # Für alle Events der Serie: Passe nur Wochentag und Uhrzeit an, das Jahr/Monat/Tag bleibt in der jeweiligen Woche erhalten
                for ev in events_to_update:
                    ev.title = data.get("title", ev.title)
                    ev.description = data.get("description", ev.description)
                    if new_start:
                        target_weekday = new_start.weekday()
                        current_date = ev.start.date()
                        days_delta = target_weekday - ev.start.weekday()
                        new_date = current_date + timedelta(days=days_delta)
                        ev_start_new = datetime.combine(new_date, new_start.timetz())
                        if timezone.is_naive(ev_start_new):
                            ev.start = timezone.make_aware(
                                ev_start_new, timezone.get_current_timezone()
                            )
                        else:
                            ev.start = ev_start_new
                    if new_end is not None:
                        if ev.end:
                            target_weekday = new_end.weekday()
                            current_date = ev.end.date()
                            days_delta = target_weekday - ev.end.weekday()
                            new_date = current_date + timedelta(days=days_delta)
                            ev_end_new = datetime.combine(new_date, new_end.timetz())
                            if timezone.is_naive(ev_end_new):
                                ev.end = timezone.make_aware(
                                    ev_end_new, timezone.get_current_timezone()
                                )
                            else:
                                ev.end = ev_end_new
                        else:
                            ev.end = None
                    ev.save()
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

    except Exception as e:
        return JsonResponse({"error": f"Fehler: {str(e)}"}, status=500)


@csrf_protect
@login_required
def export_ics(request):
    try:
        events = CalendarEvent.objects.filter(
            user=request.user
        ) | CalendarEvent.objects.filter(is_global=True)

        cal = Calendar()
        cal.add("prodid", "-//Mein Kalender//mxm.dk//")
        cal.add("version", "2.0")

        for event in events:
            from icalendar import Event as IcsEvent

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
            if getattr(event, "repeat", None) and event.repeat != "none":
                freq_map = {
                    "daily": "DAILY",
                    "weekly": "WEEKLY",
                    "monthly": "MONTHLY",
                    "yearly": "YEARLY",
                }
                freq = freq_map.get(event.repeat)
                if freq:
                    rrule = {"FREQ": freq}
                    if getattr(event, "repeat_until", None):
                        # iCalendar UNTIL muss UTC sein und als datetime
                        until = event.repeat_until
                        if timezone.is_naive(until):
                            until = timezone.make_aware(until, timezone.utc)
                        until_utc = until.astimezone(timezone.utc)
                        rrule["UNTIL"] = until_utc
                    ics_event.add("rrule", rrule)

            cal.add_component(ics_event)

        ics_content = cal.to_ical()
        response = HttpResponse(ics_content, content_type="text/calendar")
        response["Content-Disposition"] = 'attachment; filename="export.ics"'
        return response

    except Exception as e:
        messages.error(request, f"Fehler beim Exportieren: {str(e)}")
        return redirect("calendar_page")


@csrf_protect
@login_required
def import_ics(request):
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
                    group_value = title + str(now)

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
