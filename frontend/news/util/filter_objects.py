from __future__ import annotations

from typing import Any, Iterable, cast

from django.utils import translation

from ..models import (
    EmailVerteiler,
    ExterneWebsite,
    Fachschaft,
    InhaltsKategorie,
    InterneWebsite,
    Rundmail,
    Standort,
    TrustedAccountQuelle,
    Zielgruppe,
)
from .category_registry import (
    DEFAULT_LANGUAGE,
    LanguageCode,
    get_audience_category_emoji_map,
    get_content_category_emoji_map,
    get_location_emoji_map,
    get_source_emoji_map,
)

SOURCE_TYPE_IDENTIFIERS: dict[str, str] = {
    "Fachschaft": "fachschaft",
    "Interne Website": "interne_website",
    "Externe Website": "externe_website",
    "Email-Verteiler": "email_verteiler",
    "Trusted Account": "trusted_account",
    "Rundmail": "rundmail",
    "Sammel-Rundmail": "sammel_rundmail",
}


def _build_named_object_item(
    obj: Any,
    emoji_map: dict[str, str],
    relation_prefix: str,
) -> dict[str, Any]:
    """Gibt ein Dictionary mit den Attributen eines benannten Objekts zurück."""
    display_name = getattr(obj, "name", str(obj))
    slug_value = str(getattr(obj, "slug"))
    filter_field = f"{relation_prefix}__slug"

    # Emoji aus der Emoji-Map abrufen
    emoji = emoji_map.get(display_name, "")

    # Zusätzliche Behandlung für TrustedAccountQuelle
    if not emoji:
        from ..models import TrustedAccountQuelle

        if isinstance(obj, TrustedAccountQuelle):
            emoji = "👤"

    return {
        "identifier": slug_value,
        "name": display_name,
        "emoji": emoji,
        "filter_field": filter_field,
        "filter_value": slug_value,
    }


def _build_static_source_item(
    identifier: str, label: str, quelle_typ: str
) -> dict[str, Any]:
    """Gibt ein Dictionary mit den Attributen einer statischen Quelle zurück."""
    return {
        "identifier": identifier,
        "name": label,
        "emoji": "📧",
        "filter_field": "quelle_typ",
        "filter_value": quelle_typ,
    }


def _sort_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sortiert eine Liste von Objekten alphabetisch nach dem 'name'-Attribut."""
    return sorted(items, key=lambda item: item["name"].lower())


def get_objects_to_filter() -> dict[str, Any]:
    """Gibt alle Objekte zum Filtern zurück."""
    locations = Standort.objects.all()
    categories = InhaltsKategorie.objects.all()
    audiences = Zielgruppe.objects.all()
    sources = (
        list(Fachschaft.objects.all())
        + list(Rundmail.objects.all())
        + list(InterneWebsite.objects.all())
        + list(ExterneWebsite.objects.all())
        + list(EmailVerteiler.objects.all())
        + list(TrustedAccountQuelle.objects.all())
    )

    return {
        "locations": locations,
        "categories": categories,
        "audiences": audiences,
        "sources": sources,
    }


def get_objects_with_metadata() -> dict[str, list[dict[str, Any]]]:
    """Gibt Objekte zum Filtern mitsamt zugehöriger Emojis, Identifiern und Metadaten zurück."""

    # Alle Objekte zum Filtern abrufen
    objects = get_objects_to_filter()

    # Sprachcode der aktuellen Übersetzung ermitteln
    language_code = cast(LanguageCode, translation.get_language()) or DEFAULT_LANGUAGE

    # Emoji-Maps für die verschiedenen Kategorien abrufen
    location_emojis = get_location_emoji_map(language_code)
    category_emojis = get_content_category_emoji_map(language_code)
    audience_emojis = get_audience_category_emoji_map(language_code)
    source_emojis = get_source_emoji_map(language_code)

    # Standorte mit Emojis und Metadaten versehen und sortieren
    locations_with_emojis = _sort_items(
        [
            _build_named_object_item(
                loc,
                location_emojis,
                "standorte",
            )
            for loc in objects["locations"]
        ]
    )

    # Inhaltskategorien mit Emojis und Metadaten versehen und sortieren
    categories_with_emojis = _sort_items(
        [
            _build_named_object_item(
                category,
                category_emojis,
                "inhaltskategorien",
            )
            for category in objects["categories"]
        ]
    )

    # Zielgruppen mit Emojis und Metadaten versehen und sortieren
    audiences_with_emojis = _sort_items(
        [
            _build_named_object_item(
                audience,
                audience_emojis,
                "zielgruppen",
            )
            for audience in objects["audiences"]
        ]
    )

    # Quellen mit Emojis und Metadaten versehen und sortieren
    sources_with_emojis = _sort_items(
        [
            _build_named_object_item(source, source_emojis, "quelle")
            for source in objects["sources"]
            if not isinstance(source, Rundmail)
        ]
        + [
            _build_static_source_item(
                "rundmail",
                "Rundmail",
                "Rundmail",
            ),
            _build_static_source_item(
                "sammel_rundmail",
                "Sammel-Rundmail",
                "Sammel-Rundmail",
            ),
        ]
    )

    return {
        "locations": locations_with_emojis,
        "categories": categories_with_emojis,
        "audiences": audiences_with_emojis,
        "sources": sources_with_emojis,
    }
