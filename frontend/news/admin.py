import uuid
from datetime import timedelta

from django.contrib import admin, messages

from .models import *

admin.site.register(Quelle)
admin.site.register(Fachschaft)
admin.site.register(Rundmail)
admin.site.register(InterneWebsite)
admin.site.register(ExterneWebsite)
admin.site.register(EmailVerteiler)
admin.site.register(TrustedAccountQuelle)
admin.site.register(Standort)
admin.site.register(InhaltsKategorie)
admin.site.register(Zielgruppe)
admin.site.register(Sprache)
admin.site.register(Text)
admin.site.register(OpenAITokenUsage)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "is_trusted",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
    )
    list_filter = (
        "is_trusted",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = ("username", "email")
    readonly_fields = ("date_joined", "last_login")
    ordering = ("username",)


@admin.register(TrustedUserApplication)
class TrustedUserApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "user_is_trusted",
        "created_at",
        "updated_at",
        "motivation_preview",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "motivation")
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_as_approved", "mark_as_declined", "mark_as_pending"]

    @admin.display(boolean=True, description="User ist trusted?")
    def user_is_trusted(self, obj: TrustedUserApplication) -> bool:
        return obj.user.is_trusted

    @admin.display(description="Motivation")
    def motivation_preview(self, obj: TrustedUserApplication) -> str:
        preview = obj.motivation.strip()
        return (preview[:75] + "…") if len(preview) > 75 else preview

    def _set_status(self, request, queryset, status: str, success_message: str) -> None:
        updated = 0
        for application in queryset.select_related("user"):
            if application.status != status:
                application.status = status
                application.save()
            user = application.user
            if status == TrustedUserApplication.STATUS_APPROVED and not user.is_trusted:
                user.is_trusted = True
                user.save(update_fields=["is_trusted"])
            elif status == TrustedUserApplication.STATUS_DECLINED:
                if (
                    not TrustedUserApplication.objects.filter(
                        user=user,
                        status=TrustedUserApplication.STATUS_APPROVED,
                    )
                    .exclude(pk=application.pk)
                    .exists()
                    and user.is_trusted
                ):
                    user.is_trusted = False
                    user.save(update_fields=["is_trusted"])
            updated += 1
        if updated:
            self.message_user(
                request, success_message.format(count=updated), messages.SUCCESS
            )

    @admin.action(description="Auswahl genehmigen")
    def mark_as_approved(self, request, queryset):
        self._set_status(
            request,
            queryset,
            TrustedUserApplication.STATUS_APPROVED,
            "{count} Bewerbung(en) genehmigt.",
        )

    @admin.action(description="Auswahl ablehnen")
    def mark_as_declined(self, request, queryset):
        self._set_status(
            request,
            queryset,
            TrustedUserApplication.STATUS_DECLINED,
            "{count} Bewerbung(en) abgelehnt.",
        )

    @admin.action(description="Auswahl zurück auf ausstehend setzen")
    def mark_as_pending(self, request, queryset):
        self._set_status(
            request,
            queryset,
            TrustedUserApplication.STATUS_PENDING,
            "{count} Bewerbung(en) wieder auf ausstehend gesetzt.",
        )


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    # Standard-Sortierung
    ordering = ["-erstellungsdatum"]  # Absteigend sortiert (neuste zuerst)

    list_display = [
        "titel",
        "erstellungsdatum",
        "quelle",
        "bereinigt",
        "hat_kategorien",
        "vollständig_übersetzt",
    ]

    list_max_show_all = 1000

    @admin.display(boolean=True, description="Bereinigt?")
    def bereinigt(self, obj):
        return obj.is_cleaned_up

    @admin.display(boolean=True, description="Kategorien vorhanden?")
    def hat_kategorien(self, obj):
        return obj.inhaltskategorien.exists()

    @admin.display(boolean=True, description="Alle Übersetzungen vorhanden?")
    def vollständig_übersetzt(self, obj) -> bool:
        required_lang_codes = set(Sprache.objects.values_list("code", flat=True))
        existing_langs = set(obj.texte.values_list("sprache__code", flat=True))
        missing = required_lang_codes - existing_langs
        return not missing


# Kalender
# Brauchen wir um im Admin-Table Serientermine zu erstellen
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
