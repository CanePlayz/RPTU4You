import os
from datetime import datetime
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
import json
from ..forms import PreferencesForm, UserCreationForm2
from ..models import News,CalendarEvent


def news_view(request):
    return render(request, "news/News.html")


def Links(request):
    return render(request, "news/Links.html")


def login_view(request):
    next_url = request.GET.get("next", "ForYouPage")  # Standard-Weiterleitung
    
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.POST.get("next", next_url))  # Verlässlicher Redirect
        else:
            messages.error(request, "Ungültige Anmeldedaten.")
    
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
def calendar_page(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Die Kalenderseite ist nur mit Anmeldung einsehbar.")
        return redirect("login")
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

            CalendarEvent.objects.create(
                user=request.user,  # Event gehört dem aktuellen Nutzer
                title=title,
                start=start,
                end=end if end else None,
                description=description
            )

            return JsonResponse({"message": "Event erfolgreich gespeichert."}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültige JSON-Daten."}, status=400)

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

