import json
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from icalendar import Calendar
from icalendar import Event as IcsEvent
from icalendar import vRecur

from ..models import CalendarEvent
from ..my_logging import get_logger

# Maximale Anzahl an Terminen pro Serie
MAX_SERIES_OCCURRENCES = 50
# Typalias für unterschiedliche Wiederholungsintervalle
RepeatDelta = Union[timedelta, relativedelta]
# Abbildung der Wiederholungsoptionen auf ihre Zeitabstände
REPEAT_INTERVALS: Dict[str, Optional[RepeatDelta]] = {
    "none": None,
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "yearly": relativedelta(years=1),
}

# Anwendungsweiter Logger für Kalenderfunktionen
logger = get_logger(__name__)


def _parse_json(request: HttpRequest) -> Dict[str, Any]:
    # Request-Body lesen und in Python-Daten umwandeln
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        return json.loads(body or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(_("Ungültige JSON-Daten.")) from exc


def _coerce_iso_datetime(value: str, *, field: str) -> datetime:
    # ISO-String prüfen und als bewusst datierte Zeit zurückgeben
    if not value:
        raise ValueError(_("%(field)s ist erforderlich.") % {"field": field})

    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(
            _("%(field)s hat ein ungültiges Format.") % {"field": field}
        ) from exc

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    else:
        parsed = parsed.astimezone(timezone.get_current_timezone())

    return parsed


def _ensure_future(start: datetime, *, now: Optional[datetime] = None) -> None:
    # Stellt sicher dass Termine nicht in der Vergangenheit liegen
    current = now or timezone.now()
    if start < current:
        raise ValueError(
            _("Der Startzeitpunkt darf nicht in der Vergangenheit liegen.")
        )


def _get_repeat_delta(repeat: str) -> Optional[RepeatDelta]:
    # Liefert den passenden Zeitabstand für eine Wiederholung
    return REPEAT_INTERVALS.get(repeat, None)


def _generate_occurrences(
    start: datetime,
    end: Optional[datetime],
    repeat: str,
    repeat_until: datetime,
) -> list[tuple[datetime, Optional[datetime]]]:
    # Berechnet alle Vorkommen einer Terminserie bis zum Enddatum
    delta = _get_repeat_delta(repeat)
    if delta is None:
        raise ValueError(_("Unbekannter Wiederholungstyp."))

    occurrences: list[tuple[datetime, Optional[datetime]]] = []
    current_start = start
    current_end = end

    while current_start <= repeat_until:
        occurrences.append((current_start, current_end))
        if len(occurrences) > MAX_SERIES_OCCURRENCES:
            raise ValueError(_("Maximal 50 Termine pro Serie erlaubt."))

        current_start = current_start + delta
        current_end = current_end + delta if current_end else None

    if not occurrences:
        raise ValueError(_("Wiederholungsende muss nach dem Startzeitpunkt liegen."))

    return occurrences


def _serialize_event(event: CalendarEvent) -> Dict[str, Any]:
    # Wandelt ein Event in eine serielle Darstellung für JSON um
    return {
        "id": event.id,
        "title": event.title,
        "start": event.start.isoformat(),
        "end": event.end.isoformat() if event.end else None,
        "description": event.description,
        "user_id": event.user.id if event.user else None,
        "repeat": event.repeat,
        "repeat_until": event.repeat_until.isoformat() if event.repeat_until else None,
        "group": event.group,
        "is_global": event.is_global,
        "hidden": False,
    }


def _events_for_request(request: HttpRequest) -> Iterable[CalendarEvent]:
    # Bestimmt sichtbare Events abhängig von Nutzerstatus und Gruppenfilter
    group_param = request.GET.get("group")
    base_qs = CalendarEvent.objects.all().select_related("user")

    if group_param:
        return base_qs.filter(group=group_param).order_by("start")

    if request.user.is_authenticated:
        return base_qs.filter(Q(user=request.user) | Q(is_global=True)).order_by(
            "start"
        )

    return base_qs.filter(is_global=True).order_by("start")


def _generate_group_value(user_id: Any) -> str:
    # Erzeugt eine Serienkennung um zusammengehörige Events zu markieren
    prefix = user_id if user_id is not None else "global"
    return f"{prefix}-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


@login_required
def calendar_page(request: HttpRequest) -> HttpResponse:
    # Rendert die Kalenderseite für eingeloggte Nutzende
    return render(
        request,
        "news/calendar.html",
        {"is_authenticated": request.user.is_authenticated},
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calendar_events(request: HttpRequest) -> HttpResponse:
    # Liefert Eventdaten oder legt neue Events für authentifizierte Nutzende an
    if request.method == "GET":
        events = _events_for_request(request)
        return JsonResponse([_serialize_event(event) for event in events], safe=False)

    if not request.user.is_authenticated:
        return JsonResponse({"error": _("Nicht authentifiziert.")}, status=401)

    try:
        data = _parse_json(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    title = str(data.get("title", "")).strip()
    start_raw = data.get("start")
    end_raw = data.get("end")
    description = str(data.get("description", ""))
    repeat = str(data.get("repeat", "none")).lower()
    if repeat not in REPEAT_INTERVALS:
        return JsonResponse({"error": _("Unbekannter Wiederholungstyp.")}, status=400)
    repeat_until_raw = data.get("repeat_until")

    if not title or not start_raw:
        return JsonResponse(
            {"error": _("Titel und Startzeit sind erforderlich.")}, status=400
        )

    try:
        start_datetime = _coerce_iso_datetime(start_raw, field="Startzeit")
        _ensure_future(start_datetime)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    end_datetime: Optional[datetime] = None
    if end_raw:
        try:
            end_datetime = _coerce_iso_datetime(end_raw, field="Endzeit")
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        if end_datetime < start_datetime:
            return JsonResponse(
                {
                    "error": _(
                        "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."
                    )
                },
                status=400,
            )

    repeat_until: Optional[datetime] = None
    if repeat_until_raw:
        try:
            repeat_until = _coerce_iso_datetime(
                repeat_until_raw, field="Wiederholungsende"
            )
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    group_value = _generate_group_value(request.user.pk)

    try:
        if repeat != "none" and repeat_until:
            # Erstellt alle Wiederholungstermine bevor sie gespeichert werden
            occurrences = list(
                _generate_occurrences(
                    start_datetime, end_datetime, repeat, repeat_until
                )
            )
            for occurrence_start, occurrence_end in occurrences:
                CalendarEvent.objects.create(
                    user=request.user,
                    title=title,
                    start=occurrence_start,
                    end=occurrence_end,
                    description=description,
                    repeat=repeat,
                    repeat_until=repeat_until,
                    group=group_value,
                )
        else:
            CalendarEvent.objects.create(
                user=request.user,
                title=title,
                start=start_datetime,
                end=end_datetime,
                description=description,
                repeat=repeat,
                repeat_until=repeat_until,
                group=group_value,
            )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("Fehler bei der Event-Erstellung")
        return JsonResponse(
            {
                "error": _("Fehler bei der Event-Erstellung: %(error)s")
                % {"error": str(exc)}
            },
            status=500,
        )

    return JsonResponse({"message": _("Event erfolgreich gespeichert.")}, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def calendar_event_detail(request: HttpRequest, event_id) -> HttpResponse:
    # Verwaltet Einzeltermine und Serien bei Lese, Update und Löschanfragen
    event = get_object_or_404(CalendarEvent.objects.select_related("user"), id=event_id)

    if request.method == "GET":
        payload = _serialize_event(event).copy()
        payload.pop("hidden", None)
        return JsonResponse(payload)

    if request.method == "PUT":
        if not request.user.is_authenticated or (
            event.user != request.user and not request.user.is_staff
        ):
            return JsonResponse({"error": _("Keine Berechtigung.")}, status=403)

        if event.user is None and not request.user.is_staff:
            return JsonResponse(
                {"error": _("Globale Termine können nicht bearbeitet werden.")},
                status=403,
            )

        try:
            data = _parse_json(request)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        all_in_group = bool(data.get("all_in_group") and event.group)

        if all_in_group:
            # Aktualisiert eine komplette Terminserie anhand einer Änderung
            events_to_update = list(
                CalendarEvent.objects.filter(
                    group=event.group, user=event.user
                ).order_by("start")
            )
            if not events_to_update:
                return JsonResponse(
                    {"error": _("Keine Events in der Serie gefunden.")},
                    status=404,
                )

            start_value = str(data.get("start", "")).strip()
            end_present = "end" in data
            end_value = str(data.get("end", "")).strip() if end_present else ""

            new_start_dt: Optional[datetime] = None
            if start_value:
                try:
                    new_start_dt = _coerce_iso_datetime(start_value, field="Startzeit")
                except ValueError as exc:
                    return JsonResponse({"error": str(exc)}, status=400)

            new_end_dt: Optional[datetime] = None
            end_cleared = False
            if end_present:
                if end_value:
                    try:
                        new_end_dt = _coerce_iso_datetime(end_value, field="Endzeit")
                    except ValueError as exc:
                        return JsonResponse({"error": str(exc)}, status=400)
                else:
                    end_cleared = True

            ref_index = next(
                (idx for idx, ev in enumerate(events_to_update) if ev.id == event.id),
                0,
            )
            repeat_delta = _get_repeat_delta(event.repeat)

            reference_start = new_start_dt or events_to_update[ref_index].start
            if new_end_dt and new_end_dt < reference_start:
                return JsonResponse(
                    {
                        "error": _(
                            "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."
                        )
                    },
                    status=400,
                )

            for idx, ev in enumerate(events_to_update):
                if "title" in data:
                    ev.title = data["title"]
                if "description" in data:
                    ev.description = data["description"]

                if new_start_dt and repeat_delta is not None:
                    offset = idx - ref_index
                    ev.start = new_start_dt + (repeat_delta * offset)
                elif new_start_dt and repeat_delta is None and idx == ref_index:
                    ev.start = new_start_dt

                if new_end_dt and repeat_delta is not None and ev.end:
                    offset = idx - ref_index
                    ev.end = new_end_dt + (repeat_delta * offset)
                elif new_end_dt and repeat_delta is None and idx == ref_index:
                    ev.end = new_end_dt
                elif end_cleared:
                    ev.end = None

                ev.save()

            return JsonResponse({"message": _("Event-Serie erfolgreich aktualisiert.")})

        # Einzeltermin aktualisieren
        if "title" in data:
            event.title = data["title"]
        if "description" in data:
            event.description = data["description"]

        start_value = str(data.get("start", "")).strip()
        new_start = event.start
        if start_value:
            try:
                new_start = _coerce_iso_datetime(start_value, field="Startzeit")
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)

        end_present = "end" in data
        new_end = event.end
        if end_present:
            end_value = str(data.get("end", "")).strip()
            if end_value:
                try:
                    new_end = _coerce_iso_datetime(end_value, field="Endzeit")
                except ValueError as exc:
                    return JsonResponse({"error": str(exc)}, status=400)
            else:
                new_end = None

        if new_end and new_end < new_start:
            return JsonResponse(
                {
                    "error": _(
                        "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."
                    )
                },
                status=400,
            )

        event.start = new_start
        if end_present:
            event.end = new_end

        event.save()
        return JsonResponse({"message": _("Event erfolgreich aktualisiert.")})

    # DELETE Anfrage löscht den Termin
    if not request.user.is_authenticated or (
        event.user != request.user and not request.user.is_staff
    ):
        return JsonResponse({"error": _("Keine Berechtigung.")}, status=403)

    if event.user is None and not request.user.is_staff:
        return JsonResponse(
            {
                "error": _("Globale Termine können nicht gelöscht werden."),
            },
            status=403,
        )

    all_in_group = request.GET.get("all_in_group") == "true"
    if all_in_group and event.group:
        CalendarEvent.objects.filter(group=event.group, user=event.user).delete()
        return JsonResponse({"success": True, "deleted_group": True})

    event.delete()
    return JsonResponse({"success": True, "deleted_group": False})


@login_required
def export_ics(request: HttpRequest) -> HttpResponse:
    # Exportiert persönliche sowie globale Termine als ICS Datei
    try:
        events = CalendarEvent.objects.filter(
            user=request.user
        ) | CalendarEvent.objects.filter(is_global=True)

        cal = Calendar()
        cal.add("prodid", "-//Mein Kalender//mxm.dk//")
        cal.add("version", "2.0")

        for event in events:
            ics_event = IcsEvent()
            ics_event.add("summary", event.title)
            ics_event.add("dtstart", event.start)
            # dtend nur setzen wenn vorhanden
            if getattr(event, "end", None):
                ics_event.add("dtend", event.end)
            # description nur übernehmen wenn vorhanden
            if getattr(event, "description", None):
                ics_event.add("description", event.description)
            ics_event.add("uid", f"{event.id}@example.com")
            ics_event.add("dtstamp", timezone.now())

            # RRULE für Wiederholungen definieren
            if event.repeat and event.repeat != "none":
                freq_map = {
                    "daily": "DAILY",
                    "weekly": "WEEKLY",
                    "monthly": "MONTHLY",
                    "yearly": "YEARLY",
                }

                freq_value = freq_map.get(event.repeat)
                if freq_value:
                    rrule_dict: dict[str, Any] = {"FREQ": freq_value}

                    if event.repeat_until:
                        # Wiederholungsende in eine UTC Zeit übertragen
                        until = event.repeat_until

                        if timezone.is_naive(until):
                            until = timezone.make_aware(until, timezone.utc)
                        else:
                            until = until.astimezone(timezone.utc)
                        # UNTIL muss für iCalendar ohne Zeitzonenangabe vorliegen
                        rrule_dict["UNTIL"] = until.replace(tzinfo=None)

                    # RRULE als vRecur an den Termin anhängen
                    ics_event.add("rrule", vRecur(rrule_dict))

            cal.add_component(ics_event)

        ics_content = cal.to_ical()
        response = HttpResponse(ics_content, content_type="text/calendar")
        response["Content-Disposition"] = 'attachment; filename="export.ics"'
        return response

    except Exception as e:
        messages.error(
            request,
            _("Fehler beim Exportieren: %(error)s") % {"error": str(e)},
        )
        return redirect("calendar_page")


@login_required
def import_ics(request: HttpRequest) -> HttpResponse:
    # Liest eine hochgeladene ICS Datei ein und legt passende Termine an
    if request.method == "POST" and request.FILES.get("ics_file"):
        ics_file = request.FILES["ics_file"]
        file_content = ics_file.read()

        try:
            calendar = Calendar.from_ical(file_content)
            for component in calendar.walk():
                if component.name == "VEVENT":
                    title = str(component.get("summary", _("Ohne Titel")))
                    start_value = component.get("dtstart").dt
                    end_component = component.get("dtend")
                    end_value = end_component.dt if end_component else None
                    description = str(component.get("description", ""))

                    if isinstance(start_value, datetime):
                        start = (
                            start_value
                            if timezone.is_aware(start_value)
                            else timezone.make_aware(
                                start_value, timezone.get_current_timezone()
                            )
                        )
                    else:
                        start = timezone.make_aware(
                            datetime.combine(start_value, datetime.min.time()),
                            timezone.get_current_timezone(),
                        )

                    if isinstance(end_value, datetime):
                        end = (
                            end_value
                            if timezone.is_aware(end_value)
                            else timezone.make_aware(
                                end_value, timezone.get_current_timezone()
                            )
                        )
                    elif end_value:
                        end = timezone.make_aware(
                            datetime.combine(end_value, datetime.min.time()),
                            timezone.get_current_timezone(),
                        )
                    else:
                        end = None

                    # Wiederholung auslesen
                    repeat = (
                        str(component.get("rrule", {}).get("FREQ", ["none"])[0]).lower()
                        if component.get("rrule")
                        else "none"
                    )
                    if repeat not in REPEAT_INTERVALS:
                        repeat = "none"
                    repeat_until = None
                    if component.get("rrule") and "UNTIL" in component.get("rrule"):
                        until_val = component.get("rrule")["UNTIL"][0]
                        if isinstance(until_val, datetime):
                            repeat_until = until_val
                            if not timezone.is_aware(repeat_until):
                                repeat_until = timezone.make_aware(
                                    repeat_until, timezone.get_current_timezone()
                                )
                        else:
                            try:
                                repeat_until = datetime.strptime(
                                    str(until_val), "%Y%m%dT%H%M%SZ"
                                )
                                repeat_until = timezone.make_aware(
                                    repeat_until, timezone.get_current_timezone()
                                )
                            except Exception:
                                repeat_until = None

                    group_value = _generate_group_value(request.user.pk)

                    delta = _get_repeat_delta(repeat)

                    if repeat != "none" and repeat_until and delta is not None:
                        current_start = start
                        current_end = end
                        occurrences = 0
                        truncated = False

                        while current_start <= repeat_until:
                            CalendarEvent.objects.create(
                                user=request.user,
                                title=title,
                                start=current_start,
                                end=current_end,
                                description=description,
                                repeat=repeat,
                                repeat_until=repeat_until,
                                group=group_value,
                            )
                            occurrences += 1
                            if occurrences >= MAX_SERIES_OCCURRENCES:
                                truncated = current_start + delta <= repeat_until
                                break

                            current_start = current_start + delta
                            if current_end:
                                current_end = current_end + delta

                        if truncated:
                            messages.warning(
                                request,
                                _(
                                    "Beim Import wurden aus Wiederholungen nur die ersten 50 Termine angelegt."
                                ),
                            )
                    else:
                        CalendarEvent.objects.create(
                            user=request.user,
                            title=title,
                            start=start,
                            end=end,
                            description=description,
                            repeat=repeat,
                            repeat_until=repeat_until,
                            group=group_value,
                        )
            messages.success(request, _("ICS-Datei erfolgreich importiert."))
        except Exception as e:
            messages.error(
                request,
                _("Fehler beim Importieren: %(error)s") % {"error": str(e)},
            )

    return redirect("calendar_page")
