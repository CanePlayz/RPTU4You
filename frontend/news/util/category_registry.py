from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Literal

LanguageCode = Literal["de", "en", "es", "fr"]
CategoryType = Literal["content", "audience", "location", "source"]

_DATA_FILE: Final[Path] = Path(__file__).resolve().parent / "categories.json"
_CATEGORY_KEY: Final[dict[CategoryType, str]] = {
    "content": "content_categories",
    "audience": "audience_categories",
    "location": "location_categories",
    "source": "source_categories",
}


@lru_cache(maxsize=1)
def _load_category_data() -> dict[str, Any]:
    """Lädt die Kategoriedaten aus der JSON-Datei und cached sie."""
    with _DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _get_entries(category_type: CategoryType) -> list[dict[str, Any]]:
    """Extrahiert die Einträge für den angegebenen Kategorie-Typ."""
    data = _load_category_data()
    key = _CATEGORY_KEY[category_type]
    return data.get(key, [])


DEFAULT_LANGUAGE: Final[LanguageCode] = "de"


def get_content_categories(language: LanguageCode = DEFAULT_LANGUAGE) -> list[str]:
    """Gibt die geordnete Liste der Inhaltskategorienamen für die angeforderte Sprache zurück."""
    return _get_names("content", language)


def get_audience_categories(language: LanguageCode = DEFAULT_LANGUAGE) -> list[str]:
    """Gibt die geordnete Liste der Zielgruppen-Kategorienamen für die angeforderte Sprache zurück."""
    return _get_names("audience", language)


def get_location_categories(language: LanguageCode = DEFAULT_LANGUAGE) -> list[str]:
    """Gibt die geordnete Liste der Standort-Kategorienamen für die angeforderte Sprache zurück."""
    return _get_names("location", language)


def get_source_categories(language: LanguageCode = DEFAULT_LANGUAGE) -> list[str]:
    """Gibt die geordnete Liste der Quellen-Kategorienamen für die angeforderte Sprache zurück."""
    return _get_names("source", language)


def get_content_category_emoji_map(
    language: LanguageCode = DEFAULT_LANGUAGE,
) -> dict[str, str]:
    """Gibt die Zuordnung der Inhaltskategorienamen zu Emojis für die gewählte Sprache zurück.
    Beispiel: {"Kategoriename": "Emoji", ...}
    """
    return _get_emoji_map("content", language)


def get_audience_category_emoji_map(
    language: LanguageCode = DEFAULT_LANGUAGE,
) -> dict[str, str]:
    """Gibt die Zuordnung der Zielgruppen-Kategorienamen zu Emojis für die gewählte Sprache zurück.
    Beispiel: {"Kategoriename": "Emoji", ...}
    """
    return _get_emoji_map("audience", language)


def get_location_emoji_map(
    language: LanguageCode = DEFAULT_LANGUAGE,
) -> dict[str, str]:
    """Gibt die Zuordnung der Standort-Kategorienamen zu Emojis für die gewählte Sprache zurück.
    Beispiel: {"Kategoriename": "Emoji", ...}
    """
    return _get_emoji_map("location", language)


def get_source_emoji_map(
    language: LanguageCode = DEFAULT_LANGUAGE,
) -> dict[str, str]:
    """Gibt die Zuordnung der Quellen-Kategorienamen zu Emojis für die gewählte Sprache zurück.
    Beispiel: {"Kategoriename": "Emoji", ...}
    """
    return _get_emoji_map("source", language)


def _get_names(category_type: CategoryType, language: LanguageCode) -> list[str]:
    """Gibt die geordnete Liste der Kategorienamen für die angeforderte Sprache zurück."""
    names: list[str] = []
    for entry in _get_entries(category_type):
        localized_name = entry.get("names", {}).get(language)
        if not localized_name:
            continue
        names.append(localized_name)
    return names


def _get_emoji_map(
    category_type: CategoryType, language: LanguageCode
) -> dict[str, str]:
    """Gibt die Zuordnung der Kategorienamen zu Emojis für die gewählte Sprache zurück.
    Beispiel: {"Kategoriename": "Emoji", ...}
    """
    emoji_map: dict[str, str] = {}
    for entry in _get_entries(category_type):
        localized_name = entry.get("names", {}).get(language)
        if not localized_name:
            continue
        emoji = entry.get("emoji", "")
        emoji_map[localized_name] = emoji
    return emoji_map


def get_ui_icon(identifier: str) -> str:
    """Gibt das UI-Symbol für den angebenen Identifier zurück."""
    icons = _load_category_data().get("ui_icons", {})
    return icons.get(identifier, "")
