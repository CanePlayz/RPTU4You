import datetime
from typing import Optional

from django.db.models import F
from django.db.models.functions import Greatest

from ...models import OpenAITokenUsage


def reserve_tokens(
    expected_tokens: int, token_limit: int
) -> Optional[OpenAITokenUsage]:
    """Reserviert Tokens für die Nutzung und checkt das Token-Limit"""
    usage, _ = OpenAITokenUsage.objects.get_or_create(
        date=datetime.date.today(), defaults={"used_tokens": 0}
    )

    # Update kann nur erfolgreich sein, wenn das Token-Limit nicht überschritten wird
    updated = OpenAITokenUsage.objects.filter(
        pk=usage.pk, used_tokens__lte=token_limit - expected_tokens
    ).update(used_tokens=F("used_tokens") + expected_tokens)

    if not updated:
        usage.refresh_from_db()
        return None

    usage.refresh_from_db()
    return usage


def release_tokens(usage: OpenAITokenUsage, reserved_tokens: int) -> None:
    """Gibt reservierte Tokens zurück wieder frei"""
    if reserved_tokens <= 0:
        return

    OpenAITokenUsage.objects.filter(pk=usage.pk).update(
        used_tokens=Greatest(F("used_tokens") - reserved_tokens, 0)
    )
    usage.refresh_from_db()
