from __future__ import annotations

from typing import Callable, Iterable

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse
from django.utils.functional import cached_property

from .models import User


class AdminAccessRestrictionMiddleware:
    """Middleware, die den Zugriff auf Admin-Views auf Staff-User beschränkt."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._targets_admin_view(request):
            if not request.user.is_authenticated:
                login_url = reverse("login")
                return redirect(f"{login_url}?next={request.get_full_path()}")
            if not request.user.is_staff:
                raise Http404()
        return self.get_response(request)

    def _targets_admin_view(self, request: HttpRequest) -> bool:
        path = request.path_info
        try:
            match = resolve(path)
        except Resolver404:
            return False

        return self._is_admin_match(match.app_names, match.namespaces)

    @staticmethod
    def _is_admin_match(app_names: Iterable[str], namespaces: Iterable[str]) -> bool:
        admin_token = "admin"
        return admin_token in app_names or admin_token in namespaces


class UserPreferredLanguageMiddleware:
    """Middleware, die angemeldete Benutzer basierend auf ihrer bevorzugten Sprache umleitet."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._exempt_prefixes = ("/static", "/media", "/api", "/admin")

    @cached_property
    def _language_codes(self) -> set[str]:
        return {code for code, _ in settings.LANGUAGES}

    def __call__(self, request: HttpRequest) -> HttpResponse:
        redirect_target = self._build_redirect_target(request)
        if redirect_target is not None:
            return redirect(redirect_target)
        return self.get_response(request)

    def _build_redirect_target(self, request: HttpRequest) -> str | None:
        # Nur lesende Requests werden umgeleitet, um Formular-POSTs nicht zu stören.
        if request.method not in {"GET", "HEAD"}:
            return None
        if not request.user.is_authenticated or not isinstance(request.user, User):
            return None

        preferred = request.user.preferred_language
        # Ohne valide Sprache kein Redirect
        if not preferred or preferred not in self._language_codes:
            return None

        path = request.path_info or "/"
        # Statische Pfade und Admin/API-Pfade bleiben unverändert
        if any(path.startswith(prefix) for prefix in self._exempt_prefixes):
            return None

        # Bereits im bevorzugten Sprachprefix? Dann kein Redirect nötig.
        segments = [segment for segment in path.split("/") if segment]
        if segments and segments[0] in self._language_codes:
            return None

        # Set-Language-Pfade bleiben unverändert
        if path.startswith("/set-language"):
            return None

        # Pfad mit dem bevorzugten Sprachprefix konstruieren
        normalized_path = path if path.startswith("/") else f"/{path}"
        if normalized_path == "/":
            target_path = f"/{preferred}/"
        else:
            target_path = f"/{preferred}{normalized_path}"

        # Query-Parameter müssen mitgenommen werden, damit Filter erhalten bleiben
        query_string = request.META.get("QUERY_STRING", "")
        if query_string:
            target_path = f"{target_path}?{query_string}"

        return target_path
