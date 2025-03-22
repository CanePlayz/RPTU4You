import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from ..forms import PreferencesForm, UserCreationForm2
from ..models import News


def news_view(request):
    return render(request, "news/News.html")


def Links(request):
    return render(request, "news/Links.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("ForYouPage")
        else:
            messages.error(request, "Ungültige Anmeldedaten.")
    return render(request, "news/login.html")


def logout_view(request):
    logout(request)
    return redirect("news_view")


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
