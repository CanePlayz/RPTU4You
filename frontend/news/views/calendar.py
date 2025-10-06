import json
from datetime import datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from icalendar import Calendar
from icalendar import Event as IcsEvent
from icalendar import vRecur

from ..models import CalendarEvent
from ..my_logging import get_logger


@login_required
def calendar_page(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "news/calendar.html",
        {"is_authenticated": request.user.is_authenticated},
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calendar_events(request: HttpRequest) -> HttpResponse:
    # GET: Alle Events auflisten
    if request.method == "GET":
        group_param = request.GET.get("group")
        if group_param:
            # Nur Events mit diesem group-Wert zurückgeben
            events = CalendarEvent.objects.filter(group=group_param)
        elif request.user.is_authenticated:
            events = CalendarEvent.objects.filter(user=request.user)
            global_events = CalendarEvent.objects.filter(is_global=True)
            events = list(events) + list(global_events)
        else:
            events = CalendarEvent.objects.filter(is_global=True)

        event_data = [
            {
                "id": event.id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat() if event.end else None,
                "description": event.description,
                "user_id": event.user.id if event.user else None,
                "repeat": event.repeat,
                "repeat_until": (
                    event.repeat_until.isoformat() if event.repeat_until else None
                ),
                "group": event.group,
                "is_global": event.is_global,
                "hidden": False,
            }
            for event in events
        ]
        return JsonResponse(event_data, safe=False)

    # POST: Neues Event anlegen
    logger = get_logger(__name__)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Nicht authentifiziert."}, status=401)
        try:
            data = json.loads(request.body)
            title = data.get("title")
            start = data.get("start")
            end = data.get("end")
            description = data.get("description", "")
            repeat = data.get("repeat", "none")
            repeat_until_str = data.get("repeat_until")

            if not title or not start:
                return JsonResponse(
                    {"error": "Titel und Startzeit sind erforderlich."}, status=400
                )

            try:
                start_datetime = datetime.fromisoformat(start)
                start_datetime = timezone.make_aware(
                    start_datetime, timezone.get_current_timezone()
                )
            except ValueError:
                return JsonResponse(
                    {"error": "Startzeit hat ein ungültiges Format."}, status=400
                )

            now = timezone.now()

            if start_datetime < now:
                return JsonResponse(
                    {
                        "error": "Der Startzeitpunkt darf nicht in der Vergangenheit liegen."
                    },
                    status=400,
                )

            end_datetime = None
            if end:
                try:
                    end_datetime = datetime.fromisoformat(end)
                    end_datetime = timezone.make_aware(
                        end_datetime, timezone.get_current_timezone()
                    )
                except ValueError:
                    return JsonResponse(
                        {"error": "Endzeit hat ein ungültiges Format."}, status=400
                    )
                if end_datetime < start_datetime:
                    return JsonResponse(
                        {
                            "error": "Der Endzeitpunkt darf nicht vor dem Startzeitpunkt liegen."
                        },
                        status=400,
                    )

            repeat_until = None
            if repeat_until_str:
                try:
                    repeat_until = datetime.fromisoformat(repeat_until_str)
                    repeat_until = timezone.make_aware(
                        repeat_until, timezone.get_current_timezone()
                    )
                except ValueError:
                    return JsonResponse(
                        {"error": "Wiederholungsende hat ein ungültiges Format."},
                        status=400,
                    )

            events = []
            current_start = start_datetime
            current_end = end_datetime if end_datetime else None
            group_value = title + str(now)

            if repeat != "none" and repeat_until:
                if repeat == "weekly":
                    delta = timedelta(weeks=1)
                elif repeat == "daily":
                    delta = timedelta(days=1)
                elif repeat == "monthly":
                    delta = relativedelta(months=1)
                elif repeat == "yearly":
                    delta = relativedelta(years=1)
                else:
                    delta = timedelta(days=0)

                # Verhindert, dass mehr als 50 Termine pro Serie erstellt werden
                count = 0
                temp_start = current_start
                while temp_start <= repeat_until:
                    count += 1
                    temp_start += delta
                if count > 50:
                    return JsonResponse(
                        {"error": "Maximal 50 Termine pro Serie erlaubt."}, status=400
                    )

                while current_start <= repeat_until:
                    event = CalendarEvent.objects.create(
                        user=request.user,
                        title=title,
                        start=current_start,
                        end=current_end,
                        description=description,
                        repeat=repeat,
                        repeat_until=repeat_until,
                        group=group_value,
                    )
                    events.append(event)
                    current_start += delta
                    if current_end:
                        current_end += delta
            else:
                event = CalendarEvent.objects.create(
                    user=request.user,
                    title=title,
                    start=start_datetime,
                    end=end_datetime if end_datetime else None,
                    description=description,
                    repeat=repeat,
                    repeat_until=repeat_until,
                    group=group_value,
                )
                events.append(event)

            return JsonResponse(
                {"message": "Event erfolgreich gespeichert."}, status=201
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültige JSON-Daten."}, status=400)
        except Exception as e:
            error_message = f"Fehler bei der Event-Erstellung: {str(e)}"
            logger.error(error_message)
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def calendar_event_detail(request: HttpRequest, event_id) -> HttpResponse:
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        # GET: Einzelnes Event anzeigen
        if request.method == "GET":
            data = {
                "id": event.id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat() if event.end else None,
                "description": event.description,
                "user_id": event.user.id if event.user else None,
                "repeat": event.repeat,
                "repeat_until": (
                    event.repeat_until.isoformat() if event.repeat_until else None
                ),
                "group": event.group,
                "is_global": event.is_global,
            }
            return JsonResponse(data)

        # PUT: Event bearbeiten
        if request.method == "PUT":
            if not request.user.is_authenticated or (
                event.user != request.user and not request.user.is_staff
            ):
                return JsonResponse({"error": "Keine Berechtigung."}, status=403)
            # Globale Events dürfen von normalen Nutzern nicht bearbeitet werden
            if event.user is None and not request.user.is_staff:
                return JsonResponse(
                    {"error": "Globale Termine können nicht bearbeitet werden."},
                    status=403,
                )
            data = json.loads(request.body)
            all_in_group = data.get("all_in_group", False)
            if all_in_group and event.group:
                events_to_update = list(
                    CalendarEvent.objects.filter(
                        group=event.group, user=event.user
                    ).order_by("start")
                )
                if not events_to_update:
                    return JsonResponse(
                        {"error": "Keine Events in der Serie gefunden."}, status=404
                    )

                # Prüfe, ob Start/Ende geändert werden sollen
                change_start = "start" in data
                change_end = "end" in data and data["end"]

                # Berechne repeat-Delta für die Serie
                repeat_value = event.repeat
                if repeat_value == "weekly":
                    repeat_delta = timedelta(weeks=1)
                elif repeat_value == "daily":
                    repeat_delta = timedelta(days=1)
                elif repeat_value == "monthly":
                    repeat_delta = relativedelta(months=1)
                elif repeat_value == "yearly":
                    repeat_delta = relativedelta(years=1)
                else:
                    repeat_delta = None

                # Neue Start-/Endzeit für den bearbeiteten Termin
                new_start_dt = None
                new_end_dt = None
                if change_start:
                    new_start_dt = datetime.fromisoformat(data["start"])
                    if timezone.is_naive(new_start_dt):
                        new_start_dt = timezone.make_aware(
                            new_start_dt, timezone.get_current_timezone()
                        )
                if change_end:
                    new_end_dt = datetime.fromisoformat(data["end"])
                    if timezone.is_naive(new_end_dt):
                        new_end_dt = timezone.make_aware(
                            new_end_dt, timezone.get_current_timezone()
                        )

                # Finde Index des bearbeiteten Events in der Serie
                ref_index = None
                for idx, ev in enumerate(events_to_update):
                    if ev.id == event.id:
                        ref_index = idx
                        break
                if ref_index is None:
                    ref_index = 0

                # Setze alle Events neu, basierend auf repeat-Delta und Referenztermin
                for idx, ev in enumerate(events_to_update):
                    # Name und Beschreibung immer aktualisieren, falls im Request
                    if "title" in data:
                        ev.title = data["title"]
                    if "description" in data:
                        ev.description = data["description"]

                    # Startzeit aktualisieren, falls gewünscht
                    if (
                        change_start
                        and repeat_delta is not None
                        and new_start_dt is not None
                    ):
                        offset = idx - ref_index
                        ev.start = new_start_dt + (repeat_delta * offset)
                    # Endzeit aktualisieren, falls gewünscht
                    if (
                        change_end
                        and repeat_delta is not None
                        and new_end_dt is not None
                    ):
                        if ev.end:
                            offset = idx - ref_index
                            ev.end = new_end_dt + (repeat_delta * offset)
                        elif not data["end"]:
                            ev.end = None
                    ev.save()

                # ...neue Logik siehe oben...
                return JsonResponse(
                    {"message": "Event-Serie erfolgreich aktualisiert."}
                )
            else:
                # Einzeltermin
                event.title = data.get("title", event.title)
                event.description = data.get("description", event.description)
                if "start" in data:
                    start_dt = datetime.fromisoformat(data["start"])
                    if timezone.is_naive(start_dt):
                        event.start = timezone.make_aware(
                            start_dt, timezone.get_current_timezone()
                        )
                    else:
                        event.start = start_dt
                if "end" in data and data["end"]:
                    end_dt = datetime.fromisoformat(data["end"])
                    if timezone.is_naive(end_dt):
                        event.end = timezone.make_aware(
                            end_dt, timezone.get_current_timezone()
                        )
                    else:
                        event.end = end_dt
                else:
                    event.end = None
                event.save()
                return JsonResponse({"message": "Event erfolgreich aktualisiert."})

        # DELETE: Event löschen
        if request.method == "DELETE":
            if not request.user.is_authenticated or (
                event.user != request.user and not request.user.is_staff
            ):
                return JsonResponse({"error": "Keine Berechtigung."}, status=403)
            all_in_group = request.GET.get("all_in_group") == "true"
            # Globale Events: Nutzer können sie nicht löschen
            if event.user is None and not request.user.is_staff:
                return JsonResponse(
                    {"error": "Globale Termine können nicht gelöscht werden."},
                    status=403,
                )
            # Normale Events löschen
            if all_in_group and event.group:
                CalendarEvent.objects.filter(
                    group=event.group, user=event.user
                ).delete()
                return JsonResponse({"success": True, "deleted_group": True})
            else:
                event.delete()
                return JsonResponse({"success": True, "deleted_group": False})

        else:
            return JsonResponse({"error": "Methode nicht erlaubt."}, status=405)

    except Exception as e:
        return JsonResponse({"error": f"Fehler: {str(e)}"}, status=500)


@login_required
def export_ics(request: HttpRequest) -> HttpResponse:
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
            # dtend ist optional, nur setzen wenn vorhanden und nicht None
            if getattr(event, "end", None):
                ics_event.add("dtend", event.end)
            # description ist optional
            if getattr(event, "description", None):
                ics_event.add("description", event.description)
            ics_event.add("uid", f"{event.id}@example.com")
            ics_event.add("dtstamp", timezone.now())

            # RRULE für Wiederholungen setzen
            # Add RRULE for recurring events
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
                        # Ensure repeat_until is a timezone-aware UTC datetime
                        until = event.repeat_until

                        if timezone.is_naive(until):
                            until = timezone.make_aware(until, timezone.utc)
                        else:
                            until = until.astimezone(timezone.utc)
                        # iCalendar expects UTC without tzinfo for UNTIL
                        rrule_dict["UNTIL"] = until.replace(tzinfo=None)

                    # Add the RRULE as vRecur
                    ics_event.add("rrule", vRecur(rrule_dict))

            cal.add_component(ics_event)

        ics_content = cal.to_ical()
        response = HttpResponse(ics_content, content_type="text/calendar")
        response["Content-Disposition"] = 'attachment; filename="export.ics"'
        return response

    except Exception as e:
        messages.error(request, f"Fehler beim Exportieren: {str(e)}")
        return redirect("calendar_page")


@login_required
def import_ics(request: HttpRequest) -> HttpResponse:
    if request.method == "POST" and request.FILES.get("ics_file"):
        ics_file = request.FILES["ics_file"]
        file_content = ics_file.read()

        try:
            calendar = Calendar.from_ical(file_content)
            for component in calendar.walk():
                if component.name == "VEVENT":
                    title = str(component.get("summary", "Ohne Titel"))
                    start = component.get("dtstart").dt
                    end = component.get("dtend")
                    end = end.dt if end else None
                    description = str(component.get("description", ""))

                    if isinstance(start, datetime) and not timezone.is_aware(start):
                        start = timezone.make_aware(
                            start, timezone.get_current_timezone()
                        )
                    if end and isinstance(end, datetime) and not timezone.is_aware(end):
                        end = timezone.make_aware(end, timezone.get_current_timezone())

                    # Wiederholung auslesen
                    repeat = (
                        str(component.get("rrule", {}).get("FREQ", ["none"])[0]).lower()
                        if component.get("rrule")
                        else "none"
                    )
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

                    now = timezone.now()
                    # Format 'now' to exclude seconds and microseconds
                    now_formatted = now.strftime("%Y-%m-%d %H:%M")
                    group_value = title + now_formatted

                    # Mapping für FREQ zu delta
                    if repeat == "weekly":
                        delta = timedelta(weeks=1)
                    elif repeat == "daily":
                        delta = timedelta(days=1)
                    elif repeat == "monthly":
                        delta = relativedelta(months=1)
                    elif repeat == "yearly":
                        delta = relativedelta(years=1)
                    else:
                        delta = None

                    if repeat != "none" and repeat_until and delta:
                        current_start = start
                        current_end = end
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
                            current_start += delta
                            if current_end:
                                current_end += delta
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

            messages.success(request, "ICS-Datei erfolgreich importiert.")
        except Exception as e:
            messages.error(request, f"Fehler beim Importieren: {str(e)}")

    return redirect("calendar_page")
