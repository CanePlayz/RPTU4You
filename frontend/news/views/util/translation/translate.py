import datetime
import os
import re

from openai import OpenAI

from ....models import OpenAITokenUsage, Sprache
from ....my_logging import get_logger
from ..common import token_limit_reached


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

    logger = get_logger(__name__)

    if not token_limit_reached(token_limit):
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
            # Vorsorglich eine durchschnittliche Token-Nutzung speichern
            usage, _ = OpenAITokenUsage.objects.get_or_create(
                date=datetime.date.today()
            )

            usage.used_tokens += 1500
            usage.save()

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
                temperature=0.2,
            )
        except Exception as e:
            raise e
        else:
            # Tatsächlich genutzte Token in der Datenbank speichern
            usage.used_tokens -= 1500

            if response.usage:
                usage.used_tokens += response.usage.total_tokens
                usage.save()

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

    else:
        raise Exception("Token-Limit erreicht.")
