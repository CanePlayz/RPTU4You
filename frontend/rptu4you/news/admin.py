from django.contrib import admin

from .models import *

admin.site.register(Quelle)
admin.site.register(Fachschaft)
admin.site.register(Rundmail)
admin.site.register(InterneWebsite)
admin.site.register(ExterneWebsite)
admin.site.register(Standort)
admin.site.register(InhaltsKategorie)
admin.site.register(Sprache)
admin.site.register(Text)
admin.site.register(User)
admin.site.register(CalendarEvent)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    # Standard-Sortierung im Admin-Interface
    ordering = ["-erstellungsdatum"]  # Absteigend sortiert (neuste zuerst)

    # Optional: Zeige das Datum in der Liste
    list_display = ["titel", "erstellungsdatum", "quelle"]

    # Optional: Ermögliche Sortierung in der Admin-Tabelle durch Spalten-Klick
    # list_display_links = ["titel"]
