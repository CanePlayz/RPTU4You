from __future__ import annotations

import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..forms import TrustedNewsSubmissionForm, TrustedUserApplicationForm
from ..models import TrustedUserApplication, User
from ..my_logging import get_logger
from .receive_news import process_news_entry


@login_required
def trusted_news_portal(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        messages.error(request, "Ungültiger Benutzer.")
        return redirect("login")

    if user.is_trusted:
        return _handle_submission(request, user)

    return _handle_application(request, user)


def _handle_application(request: HttpRequest, user: User) -> HttpResponse:
    pending_application = TrustedUserApplication.objects.filter(
        user=user, status=TrustedUserApplication.STATUS_PENDING
    ).first()

    # Wenn eine ausstehende Bewerbung existiert, diese anzeigen
    if pending_application:
        return render(
            request,
            "news/trusted_application_status.html",
            {
                "application": pending_application,
            },
        )

    # Letzte bearbeitete Bewerbung dieses Benutzers abrufen
    last_application = (
        TrustedUserApplication.objects.exclude(
            status=TrustedUserApplication.STATUS_PENDING
        )
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    # Neues Bewerbungsformular verarbeiten
    if request.method == "POST":
        form = TrustedUserApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = user
            application.status = TrustedUserApplication.STATUS_PENDING
            application.save()
            messages.success(
                request,
                "Deine Bewerbung wurde eingereicht. Wir melden uns bei dir.",
            )
            return redirect("trusted_news_portal")
    else:
        form = TrustedUserApplicationForm()

    # Anzeige letzte Bewerbung und leeres Bewerbungsformular
    return render(
        request,
        "news/trusted_application.html",
        {
            "form": form,
            "last_application": last_application,
        },
    )


def _handle_submission(request: HttpRequest, user: User) -> HttpResponse:
    """Verarbeitung von News-Einreichungen von einem Trusted User"""
    form: TrustedNewsSubmissionForm
    # Wenn eine News gesendet wurde
    if request.method == "POST":
        form = TrustedNewsSubmissionForm(request.POST)
        if form.is_valid():
            payload = form.build_payload(user)
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_api_key:
                messages.error(
                    request,
                    "Beim Einreichen ist ein Fehler aufgetreten. Bitte versuche es später erneut.",
                )
            else:
                logger = get_logger(__name__)
                # News-Eintrag verarbeiten
                try:
                    process_news_entry(payload, openai_api_key, logger)
                except Exception:
                    logger.exception("Fehler beim Einreichen über Trusted Accounts")
                    messages.error(
                        request,
                        "Beim Einreichen ist ein Fehler aufgetreten. Bitte versuche es später erneut.",
                    )
                else:
                    messages.success(
                        request, "Deine News wurde eingereicht und wird verarbeitet."
                    )
                    # Weiterleitung zur News-Übersicht
                    return redirect("news")

    # Falls keine News gesendet wurde, leeres Formular anzeigen
    else:
        form = TrustedNewsSubmissionForm()

    return render(
        request,
        "news/trusted_submission.html",
        {
            "form": form,
        },
    )
