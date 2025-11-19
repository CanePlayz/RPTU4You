from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterable, Mapping, TypeVar, cast

from django.db.models import Model, Q
from django.db.models.query import QuerySet
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
from .categories import (
    DEFAULT_LANGUAGE,
    LanguageCode,
    get_audience_category_emoji_map,
    get_content_category_emoji_map,
    get_location_emoji_map,
    get_source_emoji_map,
)

if TYPE_CHECKING:
    from ..models import News

FilterParams = Mapping[str, Iterable[str]]
T = TypeVar("T", bound=Model)


def _build_named_object_item(
    obj: Any,
    emoji_map: dict[str, str],
    relation_prefix: str,
) -> dict[str, Any]:
    """Gibt ein Dictionary mit den Attributen eines benannten Objekts zurück."""
    display_name = getattr(obj, "name", str(obj))
    slug_value = str(getattr(obj, "slug"))
    filter_field = f"{relation_prefix}__slug"

    emoji = emoji_map.get(display_name, "")

    if not emoji and isinstance(obj, TrustedAccountQuelle):
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


def _get_objects_to_filter() -> dict[str, Any]:
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

    objects = _get_objects_to_filter()
    language_code = cast(LanguageCode, translation.get_language()) or DEFAULT_LANGUAGE

    location_emojis = get_location_emoji_map(language_code)
    category_emojis = get_content_category_emoji_map(language_code)
    audience_emojis = get_audience_category_emoji_map(language_code)
    source_emojis = get_source_emoji_map(language_code)

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


def _collect_values_by_field(
    items: Iterable[dict[str, Any]], selected_ids: Iterable[str]
) -> dict[str, list[str]]:
    """Erstellt ein Dict, das für jedes Filter-Feld die ausgewählten Werte enthält."""
    slug_item_dict = {item.get("identifier"): item for item in items}
    values_by_field: dict[str, list[str]] = defaultdict(list)
    for identifier in selected_ids:
        item = slug_item_dict.get(identifier)
        if not item:
            continue
        filter_field = item.get("filter_field")
        filter_value = item.get("filter_value", identifier)
        if not filter_field or filter_value is None:
            continue
        values_by_field[filter_field].append(str(filter_value))
    return values_by_field


def _build_or_query(values_by_field: Mapping[str, list[str]]) -> Q | None:
    """Erstellt eine OR-Abfrage für die gegebenen Filter-Felder und -Werte."""
    clauses = [
        Q(**{f"{field}__in": values})
        for field, values in values_by_field.items()
        if values
    ]
    if not clauses:
        return None

    combined_clause = clauses[0]
    for clause in clauses[1:]:
        combined_clause |= clause
    return combined_clause


def get_filtered_queryset(active_filters: FilterParams) -> QuerySet["News"]:
    """Hilfsfunktion, die News basierend auf GET-Parametern filtert."""
    from ..models import News  # lokaler Import zur Vermeidung von Zirkularität

    locations = list(active_filters.get("locations", ()))
    categories = list(active_filters.get("categories", ()))
    audiences = list(active_filters.get("audiences", ()))
    sources = list(active_filters.get("sources", ()))

    queryset = News.objects.all()
    filter_items = get_objects_with_metadata()

    location_filter = _build_or_query(
        _collect_values_by_field(filter_items["locations"], locations)
    )
    if location_filter:
        queryset = queryset.filter(location_filter)

    category_filter = _build_or_query(
        _collect_values_by_field(filter_items["categories"], categories)
    )
    if category_filter:
        queryset = queryset.filter(category_filter)

    audience_filter = _build_or_query(
        _collect_values_by_field(filter_items["audiences"], audiences)
    )
    if audience_filter:
        queryset = queryset.filter(audience_filter)

    source_filter = _build_or_query(
        _collect_values_by_field(filter_items["sources"], sources)
    )
    if source_filter:
        queryset = queryset.filter(source_filter)

    return queryset.distinct().order_by("-erstellungsdatum")


def paginate_queryset(
    queryset: QuerySet[T], offset: int = 0, limit: int = 20
) -> QuerySet[T]:
    """Schneidet ein QuerySet entsprechend Offset und Limit."""
    return queryset[offset : offset + limit]
