import datetime
import os
import random

from openai import OpenAI

from common.my_logging import get_logger

from ....models import OpenAITokenUsage
from ..common import token_limit_reached


def get_cleaned_text_from_openai(
    article_title: str, article_text: str, openai_api_key: str, token_limit: int
) -> str:
    # Dateipfade relativ zum aktuellen Verzeichnis konstruieren
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    system_message_file_path = os.path.join(BASE_DIR, "system_message.txt")

    logger = get_logger(__name__)

    if not token_limit_reached(token_limit):
        openai = OpenAI(api_key=openai_api_key)

        # Systemnachricht aus der Datei lesen und Kategorien ersetzen
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
                model="gpt-4.1-mini",
                input=[
                    {"role": "developer", "content": system_message},
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                tools=[],
                temperature=1,
            )
        except Exception as e:
            logger.error(f"Fehler bei der OpenAI-API: {e}")
            raise e
        else:
            return response.output_text.strip()
    else:
        logger.info(
            "Token-Limit erreicht. Keine Kategorien oder Zielgruppen generiert."
        )
        raise Exception(
            "Token-Limit erreicht. Keine gecleante Version des Textes generiert."
        )
