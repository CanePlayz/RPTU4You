import datetime
import os
import random

from openai import OpenAI

from common.my_logging import get_logger

from ....models import OpenAITokenUsage
from ..common import token_limit_reached


def get_categorization_from_openai(
    arctile_heading: str,
    article_text: str,
    environment: str,
    openai_api_key: str,
    token_limit: int,
) -> tuple[list[str], list[str]]:
    # Dateipfade relativ zum aktuellen Verzeichnis konstruieren
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    content_categories_file_path = os.path.join(BASE_DIR, "inhaltskategorien.txt")
    target_group_categories_file_path = os.path.join(
        BASE_DIR, "publikumskategorien.txt"
    )
    system_message_file_path = os.path.join(BASE_DIR, "system_message.txt")

    logger = get_logger(__name__)

    # Kategorien aus der Datei lesen
    with open(
        content_categories_file_path,
        "r",
        encoding="utf-8",
    ) as file:
        categories = file.read().strip().split("\n")
    with open(
        target_group_categories_file_path,
        "r",
        encoding="utf-8",
    ) as file:
        audiences = file.read().strip().split("\n")

    # Im Testumfeld zufällige Kategorien und Zielgruppen auswählen
    if environment == "dev":
        number_of_categories = len(categories)
        number_of_chosen_categories = random.randint(1, number_of_categories)
        chosen_categories = random.sample(categories, number_of_chosen_categories)

        number_of_audiences = len(audiences)
        number_of_chosen_audiences = random.randint(1, number_of_audiences)
        chosen_audiences = random.sample(audiences, number_of_chosen_audiences)

        return chosen_categories, chosen_audiences

    # Im Produktionsumfeld OpenAI-API verwenden
    else:
        if not token_limit_reached(token_limit):
            openai = OpenAI(api_key=openai_api_key)

            # Systemnachricht aus der Datei lesen und Kategorien ersetzen
            with open(
                system_message_file_path,
                "r",
                encoding="utf-8",
            ) as file:
                system_message = file.read()
            categories_str = ", ".join(categories)
            system_message = system_message.replace(
                "%Inhaltskategorien%", categories_str
            ).replace("%Publikumskategorien%", ", ".join(audiences))

            # Prompt für OpenAI-API erstellen
            prompt = f"Titel: {arctile_heading}\n\nText: {article_text}"

            # OpenAI-API aufrufen, um Kategorien und Zielgruppen zu erhalten
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
                    max_output_tokens=200,
                )
            except Exception as e:
                logger.error(f"Fehler bei der OpenAI-API: {e}")
                raise e
            else:
                # Ausgabe verarbeiten
                split_response = response.output_text.split("----")
                categories_response = split_response[0].strip()
                audiences_response = split_response[1].strip()
                categories = [
                    category.strip() for category in categories_response.split(",")
                ]
                audiences = [
                    audience.strip() for audience in audiences_response.split(",")
                ]

                # Genutzte Token in der Datenbank speichern
                usage, _ = OpenAITokenUsage.objects.get_or_create(
                    date=datetime.date.today()
                )
                if response.usage:
                    usage.used_tokens += response.usage.total_tokens
                    usage.save()

                return categories, audiences

        else:
            logger.info(
                "Token-Limit erreicht. Keine Kategorien oder Zielgruppen generiert."
            )
            return [], []
