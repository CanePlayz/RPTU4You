from typing import Iterable, Mapping, TypeVar

from django.db.models import Model, Q
from django.db.models.query import QuerySet

from ..models import News

FilterParams = Mapping[str, Iterable[str]]
T = TypeVar("T", bound=Model)


def get_filtered_queryset(active_filters: FilterParams) -> QuerySet[News]:
    """
    Hilfsfunktion, die News basierend auf GET-Parametern filtert,
    absteigend sortiert.
    """
    locations = list(active_filters.get("locations", ()))
    categories = list(active_filters.get("categories", ()))
    audiences = list(active_filters.get("audiences", ()))
    sources = list(active_filters.get("sources", ()))

    queryset = News.objects.all()
    if locations:
        queryset = queryset.filter(standorte__name__in=locations)
    if categories:
        queryset = queryset.filter(inhaltskategorien__name__in=categories)
    if audiences:
        queryset = queryset.filter(zielgruppen__name__in=audiences)
    if sources:
        rundmail_types = ["Rundmail", "Sammel-Rundmail"]
        other_sources = [src for src in sources if src not in rundmail_types]
        rundmail_sources = [src for src in sources if src in rundmail_types]

        source_filter = Q()
        if other_sources:
            source_filter |= Q(quelle__name__in=other_sources)
        if rundmail_sources:
            source_filter |= Q(quelle_typ__in=rundmail_sources)
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
