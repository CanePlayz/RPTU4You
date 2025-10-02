from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..forms import PreferencesForm, UserCreationForm2
from ..models import User


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
