from __future__ import annotations

from typing import Callable, Iterable

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse


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
