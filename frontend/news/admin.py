import hashlib
import uuid
from datetime import timedelta

from django.contrib import admin
from django.utils import timezone

from .models import *

admin.site.register(Quelle)
admin.site.register(Fachschaft)
admin.site.register(Rundmail)
admin.site.register(InterneWebsite)
admin.site.register(ExterneWebsite)
admin.site.register(EmailVerteiler)
admin.site.register(Standort)
admin.site.register(InhaltsKategorie)
admin.site.register(Zielgruppe)
admin.site.register(Sprache)
admin.site.register(Text)
admin.site.register(User)
admin.site.register(OpenAITokenUsage)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    # Standard-Sortierung
    ordering = ["-erstellungsdatum"]  # Absteigend sortiert (neuste zuerst)

    list_display = [
        "titel",
        "erstellungsdatum",
        "quelle",
        "is_cleaned_up",
        "hat_kategorien",
        "vollständig_übersetzt",
    ]

    @admin.display(boolean=True, description="Bereinigt?")
    def is_cleaned_up(self, obj):
        # Replace the following logic with the actual condition for "cleaned up"
        return obj.cleaned_up if hasattr(obj, "cleaned_up") else False

    @admin.display(boolean=True, description="Kategorien vorhanden?")
    def hat_kategorien(self, obj):
        return obj.kategorien.exists()

    @admin.display(boolean=True, description="Alle Übersetzungen vorhanden?")
    def vollständig_übersetzt(self, obj) -> bool:
        required_lang_codes = set(Sprache.objects.values_list("code", flat=True))
        existing_langs = set(obj.texte.values_list("sprache__code", flat=True))
        missing = required_lang_codes - existing_langs
        return not missing


# Kalender
# Brauchen wir um im Admin Table Serientermine zu erstellen
class CalendarEventAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "start",
        "end",
        "repeat",
        "repeat_until",
        "user",
        "is_global",
        "group",
        "description",
    )
    exclude = ("group",)

    def save_model(self, request, obj, form, change):
        # group Attribut wird automatisch gesetzt, wenn es nicht gesetzt ist
        if obj.repeat != "none" and not obj.group:
            obj.group = f"admin_{uuid.uuid4().hex}"
        # automatische Erzeugung von im Admin Tbale erstellten Serienterminen
        if not change and obj.repeat != "none" and obj.repeat_until:
            super().save_model(request, obj, form, change)
            freq = obj.repeat
            current = obj.start
            end = obj.end
            group_id = obj.group
            obj.save()
            delta = None
            if freq == "daily":
                delta = timedelta(days=1)
            elif freq == "weekly":
                delta = timedelta(weeks=1)
            elif freq == "monthly":
                from dateutil.relativedelta import relativedelta

                delta = relativedelta(months=1)
            elif freq == "yearly":
                from dateutil.relativedelta import relativedelta

                delta = relativedelta(years=1)
            else:
                delta = None
            events = []
            while True:
                if not delta:
                    break
                current = current + delta
                if current > obj.repeat_until:
                    break
                new_event = CalendarEvent(
                    title=obj.title,
                    description=obj.description,
                    start=current,
                    end=(end + (current - obj.start)) if end else None,
                    user=obj.user,
                    is_global=obj.is_global,
                    repeat="none",
                    repeat_until=None,
                    group=group_id,
                )
                events.append(new_event)
            CalendarEvent.objects.bulk_create(events)
        else:
            super().save_model(request, obj, form, change)


admin.site.register(CalendarEvent, CalendarEventAdmin)
