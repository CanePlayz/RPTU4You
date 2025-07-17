import datetime

from ...models import OpenAITokenUsage


def token_limit_reached(token_limit: int) -> bool:
    usage_today = OpenAITokenUsage.objects.filter(date=datetime.date.today()).first()
    if usage_today is None:
        return False
    if usage_today.used_tokens > token_limit:
        return True
    return False
