import datetime
import os
import random
import re

from django.db.models import F
from openai import OpenAI

from ....models import OpenAITokenUsage
from ..common import release_tokens, reserve_tokens


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

    # Inhaltskategorien und Zielgruppen aus der Datei lesen
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
        usage = reserve_tokens(1500, token_limit)

        if usage is None:
            raise Exception("Token-Limit erreicht.")

        openai = OpenAI(api_key=openai_api_key)

        # Systemnachricht aus der Datei lesen und Kategorien ersetzen
        with open(
            system_message_file_path,
            "r",
            encoding="utf-8",
        ) as file:
            system_message = file.read()
        system_message = system_message.replace(
            "%Inhaltskategorien%", ", ".join(categories)
        ).replace("%Publikumskategorien%", ", ".join(audiences))

        # Prompt für OpenAI-API erstellen
        prompt = f"Titel: {arctile_heading}\n\nText: {article_text}"

        # OpenAI-API aufrufen, um Kategorien und Zielgruppen zu erhalten
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

        # Ausgabe verarbeiten
        match = re.search(
            r"\[Inhaltskategorien\]\s*(.*?)\s*\[Publikumskategorien\]\s*(.*)",
            response.output_text,
            re.DOTALL,
        )

        # Prüfe, ob beide Teile vorhanden sind
        if not match:
            raise Exception("Inhaltskategorien oder Zielgruppen fehlen.")

        # Extrahierte Inhalte
        categories_response = match.group(1).strip().split(",")
        audiences_response = match.group(2).strip().split(",")
        categories_chatgpt = [category.strip() for category in categories_response]
        audiences_chatgpt = [audience.strip() for audience in audiences_response]

        # Überprüfen, ob die Kategorien und Zielgruppen erlaubt sind
        for category in categories_chatgpt:
            if category not in categories:
                raise Exception(f"Unbekannte Inhaltskategorie: {category}")
        for audience in audiences_chatgpt:
            if audience not in audiences:
                raise Exception(f"Unbekannte Zielgruppe: {audience}")

        return categories_chatgpt, audiences_chatgpt
