import os
from datetime import datetime
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from datetime import datetime
from django.utils import timezone 
from django.db import models
import json
from ..forms import PreferencesForm, UserCreationForm2
from ..models import News,CalendarEvent
import traceback


def news_view(request):
    now = timezone.now()  # Aktuelle Zeit mit Zeitzone

    if request.user.is_authenticated:
        # Eigene Termine des Benutzers
        user_events = CalendarEvent.objects.filter(
            start__gte=now,
            user=request.user
        )
        # Globale Termine
        global_events = CalendarEvent.objects.filter(
            start__gte=now,
            is_global=True
        )
        # Kombiniere beide Querysets und sortiere, nimm die ersten 3
        upcoming_events = (user_events | global_events).distinct().order_by('start')[:3]

    else:
        # Nicht angemeldete Benutzer: Nur globale Termine
        upcoming_events = CalendarEvent.objects.filter(
            start__gte=now,  # Nur zukünftige Termine
            is_global=True   # Nur globale Termine
        ).order_by('start')[:3]

    context = {
        'upcoming_events': upcoming_events
    }
    return render(request, "news/News.html", context)


def Links(request):
    return render(request, "news/Links.html")


def login_view(request):
    # Hole next_url aus GET oder POST, je nach Kontext
    if request.method == "POST":
        next_url = request.POST.get("next", "ForYouPage")  # Priorisiere POST nach Formularabsendung
    else:
        next_url = request.GET.get("next", "ForYouPage")   # Initialer GET-Request

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

@login_required
def calendar_page(request):
    return render(request, "news/calendar.html", {"is_authenticated": request.user.is_authenticated})

# API-Endpunkt für Kalender-Events
def calendar_events(request):
    if request.user.is_authenticated:
        events = CalendarEvent.objects.filter(user=request.user) | CalendarEvent.objects.filter(is_global=True)
    else:
        events = CalendarEvent.objects.filter(is_global=True)

    event_data = [
        {
            "id": event.id,  # Hier wird die id des Events hinzugefügt
            "title": event.title,
            "start": event.start.isoformat(),
            "end": event.end.isoformat() if event.end else None,
            "description": event.description,
            "user_id": event.user.id if event.user else None
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
                return JsonResponse({"error": "Titel und Startzeit sind erforderlich."}, status=400)

            try:
                start_datetime = datetime.fromisoformat(start)
                start_datetime = timezone.make_aware(start_datetime, timezone.get_current_timezone())
            except ValueError:
                return JsonResponse({"error": "Startzeit hat ein ungültiges Format."}, status=400)

            now = timezone.now()

            if start_datetime < now:
                return JsonResponse({"error": "Der Startzeitpunkt darf nicht in der Vergangenheit liegen."}, status=400)

            end_datetime = None
            if end:
                try:
                    end_datetime = datetime.fromisoformat(end)
                    end_datetime = timezone.make_aware(end_datetime, timezone.get_current_timezone())
                except ValueError:
                    return JsonResponse({"error": "Endzeit hat ein ungültiges Format."}, status=400)

                if end_datetime < start_datetime:
                    return JsonResponse({"error": "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."}, status=400)

            event = CalendarEvent.objects.create(
                user=request.user,
                title=title,
                start=start_datetime,
                end=end_datetime if end_datetime else None,
                description=description
            )

            return JsonResponse({"message": "Event erfolgreich gespeichert."}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültige JSON-Daten."}, status=400)
        except Exception as e:
            error_message = f"Fehler bei der Event-Erstellung: {str(e)}"
            print(error_message)
            print(traceback.format_exc())
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)

@login_required
@require_POST  # Erlaubt nur POST-Anfragen
@csrf_protect  # Stellt sicher, dass CSRF-Token geprüft wird
def delete_event(request, event_id):
    event = get_object_or_404(CalendarEvent, id=event_id)

    if event.user == request.user or request.user.is_staff:
        event.delete()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False, "error": "Keine Berechtigung"}, status=403)

