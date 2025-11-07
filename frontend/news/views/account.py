from typing import cast

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

from ..forms import (
    PreferencesForm,
    StyledPasswordChangeForm,
    UserCreationForm2,
    UsernameChangeForm,
)
from ..models import User


def _get_safe_next_url(request: HttpRequest, *, default: str = "foryoupage") -> str:
    """Return a safe redirect target that stays within the current host."""

    resolved_default = resolve_url(default)
    param_source = request.POST if request.method == "POST" else request.GET
    candidate = param_source.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return resolved_default


def login_view(request: HttpRequest) -> HttpResponse:
    next_url = _get_safe_next_url(request)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(
                request,
                "Bitte gib sowohl deinen Benutzernamen als auch dein Passwort ein.",
            )
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(next_url)
            messages.error(request, "Ungültige Anmeldedaten.")

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
    if not isinstance(request.user, User):
        messages.error(request, "Ungültiger Benutzer.")
        return redirect("login")

    user = cast(User, request.user)
    password_form = StyledPasswordChangeForm(user, prefix="password")
    username_form = UsernameChangeForm(instance=user, prefix="username")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "change_password":
            password_form = StyledPasswordChangeForm(
                user,
                request.POST,
                prefix="password",
            )
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Dein Passwort wurde erfolgreich geändert!")
                return redirect("account")
            if "old_password" in password_form.errors:
                password_form.errors["old_password"].clear()
                password_form.add_error(
                    "old_password",
                    "Das alte Passwort war falsch. Bitte neu eingeben.",
                )

        elif action == "change_username":
            username_form = UsernameChangeForm(
                request.POST,
                instance=user,
                prefix="username",
            )
            if username_form.is_valid():
                username_form.save()
                messages.success(request, "Dein Benutzername wurde geändert!")
                return redirect("account")

    return render(
        request,
        "news/account.html",
        {
            "password_form": password_form,
            "username_form": username_form,
        },
    )


@login_required
def update_preferences(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Deine Präferenzen wurden gespeichert.")
            # AJAX-Anfrage über ForYouPage
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Deine Präferenzen wurden gespeichert.",
                    }
                )
            # Nicht-AJAX-Anfragen bleiben auf der Einstellungsseite
            return redirect("preferences")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    else:
        form = PreferencesForm(instance=request.user)
    return render(request, "news/preferences.html", {"form": form})
