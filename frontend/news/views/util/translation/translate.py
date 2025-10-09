import datetime
import os
import re

from django.db.models import F
from openai import OpenAI

from ....models import OpenAITokenUsage, Sprache
from ..common import release_tokens, reserve_tokens


def translate_html(
    article_title: str,
    article_text: str,
    sprache: Sprache,
    openai_api_key: str,
    token_limit: int,
) -> tuple[str, str]:
    # Dateipfade relativ zum aktuellen Verzeichnis konstruieren
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    system_message_file_path = os.path.join(BASE_DIR, "system_message.txt")

    usage = reserve_tokens(1500, token_limit)

    if usage is None:
        raise Exception("Token-Limit erreicht.")

    openai = OpenAI(api_key=openai_api_key)

    # Systemnachricht aus der Datei lesen
    with open(
        system_message_file_path,
        "r",
        encoding="utf-8",
    ) as file:
        system_message = file.read()

    system_message = system_message.replace("%Sprache%", sprache.name_englisch)

    # Prompt für OpenAI-API erstellen
    prompt = f"Titel: {article_title} \n\nText: {article_text}"

    # OpenAI-API aufrufen, um Übersetzung des Textes zu erhalten
    try:
        response = openai.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "developer", "content": system_message},
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            tools=[],
        )
    except Exception as e:
        release_tokens(usage, 1500)
        raise e

    release_tokens(usage, 1500)

    if response.usage:
        OpenAITokenUsage.objects.filter(pk=usage.pk).update(
            used_tokens=F("used_tokens") + response.usage.total_tokens
        )
        usage.refresh_from_db()

    # Übersetzten Titel und Text zurückgeben
    match = re.search(
        r"\[Titel\]\s*(.*?)\s*\[Text\]\s*(.*)",
        response.output_text,
        re.DOTALL,
    )

    if not match:
        raise Exception("Titel oder Text fehlt.")

    translated_title = match.group(1).strip()
    translated_text = match.group(2).strip()

    return translated_title, translated_text
