import json
import os
import traceback
from datetime import datetime, timedelta

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
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from icalendar import Calendar

from ..forms import PreferencesForm, UserCreationForm2
from ..models import CalendarEvent, News, User

"""
NEWS
"""
#Info: news_view unten, bis jetzt nur Kalender auf der rechten Seite eingebunden. Jacob fragen ob man daraus zwei Views machen kann oder nicht
# Allgemine zentrale News-API, die News basierend auf verschiedenen Eingabe-Parametern zurückgibt:
# - Gefiltert nach Benutzerpräferenzen in Bezug auf Inhalt, Standort usw.
# - Mit einem Offset


# Präferenzen werden sowohl bei direktem Aufruf der Website mit Filtern als auch bei JS-Anfragen immer in URL encoded und damit immer gleich verarbeitet


# JS lädt auch aus dieser API die News, wenn die Seite geladen wird
def paginated_news(request):
    # Hole die Seite aus den GET-Parametern
    page = request.GET.get("page", 1)

    # Lade alle News und paginiere sie
    news_list = News.objects.all().order_by("-erstellungsdatum")
    paginator = Paginator(news_list, 10)  # 10 News pro Seite

    try:
        news_page = paginator.page(page)
    except:
        return JsonResponse({"error": "Invalid page number"}, status=400)

    news_data = [
        {
            "id": news.id,
            "titel": news.titel,
            "text": news.text,
            "erstellungsdatum": news.erstellungsdatum.strftime("%d.%m.%Y %H:%M:%S"),
            "link": news.link,
            "quelle_typ": news.quelle_typ,  # Annahme, dass Quelle als Typ gespeichert ist
        }
        for news in news_page
    ]

    # JSON-Objekte in fertigen, auslieferbaren HTML-Code umwandeln

    return JsonResponse({"news": news_data, "next_page": news_page.has_next()})


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

    # Prüfen, ob News-Objekte vorhanden sind
    if not News.objects.exists():
        return JsonResponse({"error": "No news available"}, status=404)

    date: datetime = News.objects.latest("erstellungsdatum").erstellungsdatum

    return JsonResponse({"date": date.strftime("%d.%m.%Y %H:%M:%S")})


# Alternative mit Nachricht für nicht angemeldete Benutzer
from django.contrib.auth.decorators import login_required


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

# API-Endpunkt für Kalender-Events
def calendar_events(request):
    if request.user.is_authenticated:
        events = CalendarEvent.objects.filter(
            user=request.user
        ) | CalendarEvent.objects.filter(is_global=True)
    else:
        events = CalendarEvent.objects.filter(is_global=True)

    event_data = [
        {
            "id": event.id,  # Hier wird die id des Events hinzugefügt
            "title": event.title,
            "start": event.start.isoformat(),
            "end": event.end.isoformat() if event.end else None,
            "description": event.description,
            "user_id": event.user.id if event.user else None,
        }
        for event in events
    ]

    return JsonResponse(event_data, safe=False)


@csrf_protect  # CSRF-Schutz aktivieren
@login_required
def create_event(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title")
            start = data.get("start")
            end = data.get("end")
            description = data.get("description", "")

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

            repeat = data.get("repeat", "none")
            repeat_until_str = data.get("repeat_until")

            repeat_until = None
            if repeat_until_str:
                try:
                    repeat_until = datetime.fromisoformat(repeat_until_str)
                    repeat_until = timezone.make_aware(repeat_until, timezone.get_current_timezone())
                except ValueError:
                    return JsonResponse({"error": "Wiederholungsende hat ein ungültiges Format."}, status=400)

            events = []
            current_start = start_datetime
            current_end = end_datetime if end_datetime else None

            if repeat != "none" and repeat_until:
                delta = timedelta(weeks=1) if repeat == "weekly" else timedelta(days=1)

                while current_start <= repeat_until:
                    event = CalendarEvent.objects.create(
                        user=request.user,
                        title=title,
                        start=current_start,
                        end=current_end,
                        description=description,
                        repeat=repeat,
                        repeat_until=repeat_until,
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
                )
                events.append(event)


            return JsonResponse(
                {"message": "Event erfolgreich gespeichert."}, status=201
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültige JSON-Daten."}, status=400)
        except Exception as e:
            error_message = f"Fehler bei der Event-Erstellung: {str(e)}"
            print(error_message)
            print(traceback.format_exc())
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)

@csrf_protect
@login_required
@require_POST
def edit_event(request, event_id):
    event = get_object_or_404(CalendarEvent, id=event_id, user=request.user)

    try:
        data = json.loads(request.body)

        event.title = data.get("title", event.title)
        event.description = data.get("description", event.description)
        
        if "start" in data:
            start = datetime.fromisoformat(data["start"])
            event.start = timezone.make_aware(start, timezone.get_current_timezone())

        if "end" in data and data["end"]:
            end = datetime.fromisoformat(data["end"])
            event.end = timezone.make_aware(end, timezone.get_current_timezone())
        else:
            event.end = None

        event.repeat = data.get("repeat", event.repeat)
        repeat_until_str = data.get("repeat_until")
        if repeat_until_str:
            event.repeat_until = timezone.make_aware(datetime.fromisoformat(repeat_until_str), timezone.get_current_timezone())
        else:
            event.repeat_until = None

        event.save()

        return JsonResponse({"message": "Event erfolgreich aktualisiert."})

    except Exception as e:
        return JsonResponse({"error": f"Fehler: {str(e)}"}, status=500)


@login_required
@require_POST  # Erlaubt nur POST-Anfragen
@csrf_protect  # Stellt sicher, dass CSRF-Token geprüft wird
def delete_event(request, event_id):
    event = get_object_or_404(CalendarEvent, id=event_id)

    if event.user == request.user or request.user.is_staff:
        event.delete()
        return JsonResponse({"success": True})
    else:
        return JsonResponse(
            {"success": False, "error": "Keine Berechtigung"}, status=403
        )


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
            if event.end:
                ics_event.add("dtend", event.end)
            if event.description:
                ics_event.add("description", event.description)
            ics_event.add("uid", f"{event.id}@example.com")
            ics_event.add("dtstamp", timezone.now())
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

                    CalendarEvent.objects.create(
                        user=request.user,
                        title=title,
                        start=start,
                        end=end,
                        description=description,
                    )

            messages.success(request, "ICS-Datei erfolgreich importiert.")
        except Exception as e:
            messages.error(request, f"Fehler beim Importieren: {str(e)}")

    return redirect("calendar_page")
