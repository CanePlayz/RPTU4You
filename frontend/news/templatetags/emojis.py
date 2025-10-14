# Emoji-Filter für Kategorie, Standort und Zielgruppe
from django import template
from ..util.kategorien_emojis import CATEGORY_EMOJIS, LOCATION_EMOJIS, AUDIENCE_EMOJIS

register = template.Library()

@register.filter
def kategorie_emoji(name):
    return CATEGORY_EMOJIS.get(name, "")

@register.filter
def standort_emoji(name):
    return LOCATION_EMOJIS.get(name, "")

@register.filter
def zielgruppe_emoji(name):
    return AUDIENCE_EMOJIS.get(name, "")
