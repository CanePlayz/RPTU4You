from datetime import datetime


def create_news_entry(
    link: str,
    title: str,
    date: datetime,
    text: str,
    locations: list[str],
    source_type: str,
    source_name: str,
) -> dict:

    return {
        "link": link,
        "titel": title,
        "erstellungsdatum": date,
        "text": text,
        "standorte": locations,
        "quelle_typ": source_type,
        "quelle_name": source_name,
    }
