import json

import scraper.util.frontend_interaction as frontend_interaction


def save_as_json(news: list, filename: str) -> None:
    for entry in news:
        entry["text"] = entry["text"].replace('"', "'")
    json_data = json.dumps(
        news, ensure_ascii=False, default=frontend_interaction.datetime_serializer
    )
    json_data_encoded = json_data.encode("utf-8")
    with open(f"{filename}.json", "wb") as file:
        file.write(json_data_encoded)
