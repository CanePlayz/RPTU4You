from collections import defaultdict
from typing import Any, Iterable, Mapping, TypeVar

from django.db.models import Model, Q
from django.db.models.query import QuerySet

from ..models import News
from ..util.filter_objects import get_objects_with_metadata

FilterParams = Mapping[str, Iterable[str]]
T = TypeVar("T", bound=Model)


def _collect_values_by_field(
    items: Iterable[dict[str, Any]], selected_ids: Iterable[str]
) -> dict[str, list[str]]:
    """Erstellt ein Dict, das für jedes Filter-Feld die ausgewählten Werte enthält."""
    # Dict aus Slug zu Item für schnellen Zugriff erstellen
    slug_item_dict = {item.get("identifier"): item for item in items}
    values_by_field: dict[str, list[str]] = defaultdict(list)
    # Für jedes Parameter der User-Query
    for identifier in selected_ids:
        # Entsprechendes Item aus dem Dict holen
        item = slug_item_dict.get(identifier)
        if not item:
            continue
        # Filter-Feld und -Wert extrahieren
        filter_field = item.get("filter_field")
        filter_value = item.get("filter_value", identifier)
        if not filter_field or filter_value is None:
            continue
        # Für jedes Filter-Feld die Werte sammeln (bspw. für standorte_slug: [slug1, slug2])
        values_by_field[filter_field].append(str(filter_value))
    return values_by_field


def _build_or_query(values_by_field: Mapping[str, list[str]]) -> Q | None:
    """Erstellt eine OR-Abfrage für die gegebenen Filter-Felder und -Werte."""
    # Einzelne Abfrage-Klauseln für jedes Filter-Feld erstellen
    clauses = [
        Q(**{f"{field}__in": values})
        for field, values in values_by_field.items()
        if values
    ]
    if not clauses:
        return None

    # Alle Klauseln mit OR verknüpfen
    combined_clause = clauses[0]
    for clause in clauses[1:]:
        combined_clause |= clause
    return combined_clause


def get_filtered_queryset(active_filters: FilterParams) -> QuerySet[News]:
    """
    Hilfsfunktion, die News basierend auf GET-Parametern filtert,
    absteigend sortiert.
    """
    # Extrahiere die Filterkriterien aus den GET-Parametern
    locations = list(active_filters.get("locations", ()))
    categories = list(active_filters.get("categories", ()))
    audiences = list(active_filters.get("audiences", ()))
    sources = list(active_filters.get("sources", ()))

    # News und Filterobjekte laden
    queryset = News.objects.all()
    filter_items = get_objects_with_metadata()

    # Filterkriterien für Standorte anwenden
    # Filter aufbauen und anwenden
    location_filter = _build_or_query(
        _collect_values_by_field(filter_items["locations"], locations)
    )
    if location_filter:
        queryset = queryset.filter(location_filter)

    # Filterkriterien für Inhaltskategorien anwenden
    # Filter aufbauen und anwenden
    category_filter = _build_or_query(
        _collect_values_by_field(filter_items["categories"], categories)
    )
    if category_filter:
        queryset = queryset.filter(category_filter)

    # Filterkriterien für Zielgruppen anwenden
    # Filter aufbauen und anwenden
    audience_filter = _build_or_query(
        _collect_values_by_field(filter_items["audiences"], audiences)
    )
    if audience_filter:
        queryset = queryset.filter(audience_filter)

    # Filterkriterien für Quellen anwenden
    # Filter aufbauen und anwenden
    source_filter = _build_or_query(
        _collect_values_by_field(filter_items["sources"], sources)
    )
    if source_filter:
        queryset = queryset.filter(source_filter)

    return queryset.distinct().order_by("-erstellungsdatum")


def paginate_queryset(
    queryset: QuerySet[T], offset: int = 0, limit: int = 20
) -> QuerySet[T]:
    """
    Schneidet ein QuerySet entsprechend Offset und Limit.
    Standard-Werte für offset und limit kommen zum Zug, wenn die
    News-Seite neu geladen wird. Standardmäßig werden also 20
    News-Objekte an den Client gesendet, bevor JS auf dem Client
    weitere News anfordert.
    """
    return queryset[offset : offset + limit]
