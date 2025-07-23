from typing import Any

from ..models import *
from .kategorien_emojis import (
    AUDIENCE_EMOJIS,
    CATEGORY_EMOJIS,
    LOCATION_EMOJIS,
    SOURCES_EMOJIS,
)


def get_objects_to_filter() -> dict[str, Any]:
    locations = Standort.objects.all()
    categories = InhaltsKategorie.objects.all()
    audiences = Zielgruppe.objects.all()
    sources = (
        list(Fachschaft.objects.all())
        + list(Rundmail.objects.all())
        + list(InterneWebsite.objects.all())
        + list(ExterneWebsite.objects.all())
        + list(EmailVerteiler.objects.all())
        + [q for q in Quelle.objects.all() if type(q) is Quelle]
    )

    return {
        "locations": locations,
        "categories": categories,
        "audiences": audiences,
        "sources": sources,
    }


def get_objects_with_emojis() -> dict[str, list[dict[str, str]]]:
    """
    Gibt Objekte mit Emojis für HTML-Rendering zurück.

    Format: {
        "locations": [{"name": "Kaiserslautern", "emoji": "🏙️"}, ...],
        "categories": [{"name": "Forschung", "emoji": "🔬"}, ...],
        "audiences": [{"name": "Studierende", "emoji": "🎓"}, ...],
        "sources": [{"name": "Quelle1", "emoji": "📧"}, ...]
    }
    """
    # Objekte abrufen
    objects = get_objects_to_filter()

    # Emojis zu den Standorten hinzufügen, abhängig vom Namen des Objekts
    locations_with_emojis = [
        {"name": loc.name, "emoji": LOCATION_EMOJIS.get(loc.name, "")}
        for loc in objects["locations"]
    ]

    # Emojis zu den Inhaltskategorien hinzufügen, abhängig vom Namen der Kategorie
    categories_with_emojis = [
        {"name": cat.name, "emoji": CATEGORY_EMOJIS.get(cat.name, "")}
        for cat in objects["categories"]
    ]

    # Emojis zu den Zielgruppen hinzufügen, abhängig vom Namen der Zielgruppe
    audiences_with_emojis = [
        {"name": aud.name, "emoji": AUDIENCE_EMOJIS.get(aud.name, "")}
        for aud in objects["audiences"]
    ]

    # Emojis zu den Quellen hinzufügen, abhängig vom Typ der Quelle
    sources_with_emojis = []
    for src in objects["sources"]:
        if isinstance(src, Fachschaft):
            emoji = SOURCES_EMOJIS.get("Fachschaft", "")
        elif isinstance(src, Rundmail):
            emoji = SOURCES_EMOJIS.get("Rundmail", "")
        elif isinstance(src, InterneWebsite):
            emoji = SOURCES_EMOJIS.get("Interne Website", "")
        elif isinstance(src, ExterneWebsite):
            emoji = SOURCES_EMOJIS.get("Externe Website", "")
        elif isinstance(src, EmailVerteiler):
            emoji = SOURCES_EMOJIS.get("Email-Verteiler", "")
        else:
            emoji = SOURCES_EMOJIS.get("Quelle", "")
        sources_with_emojis.append({"name": src.name, "emoji": emoji})

    return {
        "locations": locations_with_emojis,
        "categories": categories_with_emojis,
        "audiences": audiences_with_emojis,
        "sources": sources_with_emojis,
    }
