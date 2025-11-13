import datetime
import os
import re

from django.db.models import F
from openai import OpenAI

from ....models import OpenAITokenUsage
from ..common import release_tokens, reserve_tokens


def get_cleaned_text_from_openai(
    article_title: str, article_text: str, openai_api_key: str, token_limit: int
) -> str:
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

    # Prompt für OpenAI-API erstellen
    prompt = f"Titel: {article_title} \n\nText: {article_text}"

    # OpenAI-API aufrufen, um gecleante Version des Textes zu erhalten
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

    return response.output_text.strip()


def extract_parts(response_text: str) -> dict[str, str]:
    match_de = re.search(
        r"\[LANGUAGE:de\]\s*\[Titel\]\s*(.*?)\s*\[Text\]\s*(.*?)\s*(?=\[LANGUAGE:|$)",
        response_text,
        re.DOTALL,
    )

    match_en = re.search(
        r"\[LANGUAGE:en\]\s*\[Titel\]\s*(.*?)\s*\[Text\]\s*(.*?)\s*(?=\[LANGUAGE:|$)",
        response_text,
        re.DOTALL,
    )

    # Prüfe, ob beide Teile vorhanden sind
    has_de = match_de is not None
    has_en = match_en is not None

    if not has_de or not has_en:
        raise Exception("Es wurde nicht für beide Sprachen ein Text gefunden.")

    # Extrahierte Inhalte
    cleaned_title_de = match_de.group(1).strip() if match_de else ""
    cleaned_text_de = match_de.group(2).strip() if match_de else ""
    cleaned_title_en = match_en.group(1).strip() if match_en else ""
    cleaned_text_en = match_en.group(2).strip() if match_en else ""

    return {
        "cleaned_title_de": cleaned_title_de,
        "cleaned_text_de": cleaned_text_de,
        "cleaned_title_en": cleaned_title_en,
        "cleaned_text_en": cleaned_text_en,
    }
