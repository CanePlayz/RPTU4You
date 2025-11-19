# Emoji-Filter für Kategorie, Standort, Zielgruppe und generische UI-Icons
from functools import lru_cache
from typing import cast

from django import template
from django.utils import translation

from ..util.category_registry import (
    DEFAULT_LANGUAGE,
    LanguageCode,
    get_audience_category_emoji_map,
    get_content_category_emoji_map,
    get_location_emoji_map,
    get_ui_icon,
)

register = template.Library()


def _resolve_language() -> LanguageCode:
    code = translation.get_language()
    return cast(LanguageCode, code)


@lru_cache(maxsize=None)
def _category_emojis(language: LanguageCode) -> dict[str, str]:
    return get_content_category_emoji_map(language)


@lru_cache(maxsize=None)
def _location_emojis(language: LanguageCode) -> dict[str, str]:
    return get_location_emoji_map(language)


@lru_cache(maxsize=None)
def _audience_emojis(language: LanguageCode) -> dict[str, str]:
    return get_audience_category_emoji_map(language)


@register.filter
def kategorie_emoji(name):
    language = _resolve_language()
    return _category_emojis(language).get(name, "")


@register.filter
def standort_emoji(name):
    language = _resolve_language()
    return _location_emojis(language).get(name, "")


@register.filter
def zielgruppe_emoji(name):
    language = _resolve_language()
    return _audience_emojis(language).get(name, "")


@register.simple_tag
def ui_icon(identifier):
    return get_ui_icon(identifier)
