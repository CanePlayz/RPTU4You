from __future__ import annotations

import os
import threading

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from ..forms import TrustedNewsSubmissionForm, TrustedUserApplicationForm
from ..models import TrustedUserApplication, User
from ..my_logging import get_logger
from .receive_news import process_news_entry


@login_required
def trusted_news_portal(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return redirect("login")

    if user.is_trusted:
        return _handle_submission(request, user)

    return _handle_application(request, user)


def _send_trusted_application_notification(username: str, motivation: str) -> None:
    """Sendet die Trusted-Application-Mail außerhalb des Request-Threads."""
    logger = get_logger(__name__)
    recipient = (os.getenv("EMAIL_JACOB") or "").strip()

    project_mail = (os.getenv("IMAP_USERNAME") or "").strip() or None
    message = _(
        "Der Benutzer %(username)s hat sich als Trusted User beworben.\n\n"
        "Motivation:\n%(motivation)s\n\n"
        "Bitte überprüfe die Bewerbung im Admin-Panel."
    ) % {
        "username": username,
        "motivation": motivation,
    }

    try:
        with mail.get_connection() as connection:
            send_mail(
                subject=_("Neue Trusted-User-Bewerbung eingegangen"),
                message=message,
                from_email=project_mail,
                recipient_list=[recipient],
                fail_silently=False,
                connection=connection,
            )
    except Exception:
        logger.exception(
            "Fehler beim Senden der Trusted-User-Benachrichtigung per E-Mail"
        )


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

    # Eingereichtes Bewerbungsformular verarbeiten
    if request.method == "POST":
        form = TrustedUserApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = user
            application.status = TrustedUserApplication.STATUS_PENDING
            application.save()

            try:
                # Benachrichtigung in eigenem Thread senden, damit der Request nicht blockiert wird
                threading.Thread(
                    target=_send_trusted_application_notification,
                    args=(application.user.username, application.motivation),
                    daemon=True,
                ).start()
            except Exception:
                logger = get_logger(__name__)
                logger.exception("Fehler beim Starten der Bewerbungsbenachrichtigung")

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
                    _(
                        "Beim Einreichen ist ein Fehler aufgetreten. Bitte versuche es später erneut."
                    ),
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
                        _(
                            "Beim Einreichen ist ein Fehler aufgetreten. Bitte versuche es später erneut."
                        ),
                    )
                else:
                    messages.success(
                        request,
                        _("Deine News wurde eingereicht und wird verarbeitet."),
                    )
                    form = TrustedNewsSubmissionForm()

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
