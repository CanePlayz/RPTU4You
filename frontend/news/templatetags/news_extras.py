from __future__ import annotations

from django import template
from django.utils.translation import get_language

from ..models import News

register = template.Library()


@register.filter(name="get_translated_title")
def get_translated_title(news: News) -> str:
    """Gibt den übersetzten Titel der News basierend auf der aktuellen Sprache zurück."""

    language = get_language()
    if not language:
        return news.titel

    return news.get_translated_title(language)
