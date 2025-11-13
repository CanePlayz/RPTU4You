# Emoji-Filter für Kategorie, Standort, Zielgruppe und generische UI-Icons
from django import template

from ..util.category_registry import (
    get_audience_category_emoji_map,
    get_content_category_emoji_map,
    get_location_emoji_map,
    get_ui_icon,
)

register = template.Library()

# Durch DEFAULT_LANGUAGE in den Funktionen werden hier die deutschen Emoji-Maps geladen
# Da die Templates mit den Name-Attribute der Objekte arbeiten, die die deutschen Namen enthalten, funktioniert das so
_CATEGORY_EMOJIS = get_content_category_emoji_map()
_LOCATION_EMOJIS = get_location_emoji_map()
_AUDIENCE_EMOJIS = get_audience_category_emoji_map()


@register.filter
def kategorie_emoji(name):
    return _CATEGORY_EMOJIS.get(name, "")


@register.filter
def standort_emoji(name):
    return _LOCATION_EMOJIS.get(name, "")


@register.filter
def zielgruppe_emoji(name):
    return _AUDIENCE_EMOJIS.get(name, "")


@register.simple_tag
def ui_icon(identifier):
    return get_ui_icon(identifier)
