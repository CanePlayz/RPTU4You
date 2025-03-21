import json

import bs4
import requests
import scraper.util.send_to_frontend as send_to_frontend


def fetch_rundmail_archive() -> str:
    # Archiv-Seite der Rundmail aufrufen
    return requests.get("https://rundmail.rptu.de/archive").text


def parse_rundmail_archive(html: str) -> list[bs4.element.Tag]:
    # Archiv-Seite in BeautifulSoup-Objekt umwandeln
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html, "html.parser")
    # Alle Einträge im Archiv extrahieren
    return soup.find_all(name="tr")[1:]  # type: ignore


def remove_fixes(subject: str) -> str:
    # Präfixe und Suffixe entfernen
    replacements: list[str] = [
        "[Mitarbeitende] ",
        "[Studierende] ",
        " #KL",
        " #LD",
    ]
    subject_processed: str = subject
    for r in replacements:
        subject_processed = subject_processed.replace(r, "")

    return subject_processed


def clean_text(text: str) -> str:
    # Unicode-Zeichen für Zeilenumbrüche entfernen
    text_processed: str = text.replace("\\r\\n", "<br>")
    # Escaping von Anführungszeichen entfernen
    text_processed: str = text.replace('\\"', '"')

    return text_processed


def extract_locations(subject: str) -> list:
    # Standorte aus Subject extrahieren
    if subject.endswith("#KL"):
        return ["Kaiserslautern"]
    elif subject.endswith("#LD"):
        return ["Landau"]
    else:
        return ["Kaiserslautern", "Landau"]


def extract_categories(subject: str, category_name: str) -> list[str]:
    # Kategorien aus Subject und Kategoriename extrahieren
    categories = []

    if subject.startswith("[Mitarbeitende]"):
        categories.append("Mitarbeitende")
    if subject.startswith("[Studierende]"):
        categories.append("Studierende")

    if category_name == "Veranstaltungen":
        categories.append("Veranstaltung")
    elif category_name == "Umfragen":
        categories.append("Umfrage")

    return categories


def create_news_entry(
    link: str,
    title: str,
    date: str,
    text: str,
    locations: list,
    categories: list[str],
    source_type: str,
    rundmail_id: str,
) -> dict:
    # Name der Quelle ist bei Einzel-Rundmails der Titel und bei Sammel-Rundmails "Sammel-Rundmail vom <Datum>"
    if source_type == "Rundmail":
        quelle_name = title
    elif source_type == "Sammel-Rundmail":
        quelle_name = f"Sammel-Rundmail vom {date.split()[0]}"
    elif source_type == "Stellenangebote Sammel-Rundmail":
        quelle_name = f"Stellenangebote Sammel-Rundmail vom {date.split()[0]}"

    return {
        "link": link,
        "titel": title,
        "erstellungsdatum": date,
        "text": text,
        "standorte": locations,
        "kategorien": categories,
        "quelle_typ": source_type,
        "quelle_name": quelle_name,
        "rundmail_id": rundmail_id,
    }


def process_archive_entry(archive_entry: bs4.element.Tag) -> dict | list[dict]:
    # Link zu Archiv-Eintrag extrahieren
    link = archive_entry.find(name="a")
    if isinstance(link, bs4.element.Tag):
        href = link.get("href")
    complete_link: str = f"https://rundmail.rptu.de{href}"

    # Archiv-Eintrag aufrufen und in BeautifulSoup-Objekt umwandeln
    archive_entry_html: str = requests.get(complete_link).text
    archive_entry_soup: bs4.BeautifulSoup = bs4.BeautifulSoup(
        archive_entry_html, "html.parser"
    )

    if isinstance(archive_entry_soup, bs4.element.Tag):
        # Datum extrahieren
        date = archive_entry.find(name="td", class_="created_at")
        if isinstance(date, bs4.element.Tag):
            datum_clean: str = date.text.strip()

        # Subject extrahieren
        subject = archive_entry.find(name="td", class_="subject")
        if isinstance(subject, bs4.element.Tag):
            subject_clean: str = subject.text.strip()

    # Archiv-Eintrag verarbeiten
    if subject_clean.startswith("Sammel-Rundmail"):
        return process_sammel_rundmail(
            archive_entry_soup,
            complete_link,
            datum_clean,
        )
    elif subject_clean.startswith("Stellenangebote Sammel-Rundmail"):
        return process_sammel_rundmail(
            archive_entry_soup,
            complete_link,
            datum_clean,
            stellenangebote=True,
        )
    else:
        return process_rundmail(
            archive_entry_soup,
            complete_link,
            datum_clean,
            subject_clean,
        )


def process_sammel_rundmail(
    archive_entry_soup: bs4.BeautifulSoup,
    link: str,
    date: str,
    stellenangebote: bool = False,
) -> list[dict]:
    news_of_archive_entry: list[dict] = []

    # Message-Overview finden
    messages_overview = archive_entry_soup.find(name="div", class_="messages-overview")

    # Rundmail-ID extrahieren
    rundmail_id = link.split("/")[-1]

    # Kategorien extrahieren
    if isinstance(messages_overview, bs4.element.Tag):
        categories_in_archive_entry: bs4.ResultSet[bs4.element.Tag] = (
            messages_overview.find_all(name="h5", class_="mt-4")
        )  # type: ignore

    # Einträge in allen Kategorien verarbeiten
    for category in categories_in_archive_entry:
        # Kategorienamen und Einträge extrahieren
        category_name: str = category.text
        category_list_with_news_entries = category.find_next_sibling(name="ul")
        if isinstance(category_list_with_news_entries, bs4.element.Tag):
            news_entries_in_category: bs4.ResultSet[bs4.element.Tag] = (
                category_list_with_news_entries.find_all(name="li")
            )  # type: ignore

        # Einträge in Kategorie verarbeiten
        for news_entry in news_entries_in_category:
            # Subject und Eintrag-ID extrahieren
            a_element = news_entry.find(name="a")
            if isinstance(a_element, bs4.element.Tag):
                news_entry_subject: str = a_element.text
                news_entry_id = a_element.get("href")
                if isinstance(news_entry_id, str):
                    news_entry_id_clean: str = news_entry_id.replace("#", "")

            # Eintrag aufrufen und daraus Text extrahieren
            news_entry_heading = archive_entry_soup.find(
                name="h2", id=news_entry_id_clean
            )
            if isinstance(news_entry_heading, bs4.element.Tag):
                news_entry_body = news_entry_heading.find_next_sibling(name="div")
                if isinstance(news_entry_body, bs4.element.Tag):
                    news_text = news_entry_body.find(name="p", class_="whitespaces")
                    if isinstance(news_text, bs4.element.Tag):
                        news_text_without_tag: str = news_text.decode_contents()

            # Standorte und Kategorien extrahieren
            locations: list[str] = extract_locations(news_entry_subject)
            extracted_categories: list[str] = extract_categories(
                news_entry_subject, category_name
            )

            # Präfixe und Suffixe entfernen
            news_entry_subject_clean: str = remove_fixes(news_entry_subject)

            # Eintrag erstellen
            news_of_archive_entry.append(
                create_news_entry(
                    f"{link}#{news_entry_id}",
                    news_entry_subject_clean,
                    date,
                    news_text_without_tag,
                    locations,
                    extracted_categories,
                    (
                        "Sammel-Rundmail"
                        if not stellenangebote
                        else "Stellenangebote Sammel-Rundmail"
                    ),
                    rundmail_id,
                )
            )

    return news_of_archive_entry


def process_rundmail(
    archive_entry_soup: bs4.BeautifulSoup, link: str, date: str, subject: str
) -> dict:
    # p-Element mit Text finden
    text_element = archive_entry_soup.find(name="p", class_="whitespaces")

    # Text aus p-Element extrahieren
    if isinstance(text_element, bs4.element.Tag):
        text = text_element.decode_contents()
    else:
        exit()

    # Standorte aus Subject extrahieren
    locations: list[str] = extract_locations(subject)

    # Präfixe und Suffixe entfernen
    subject_clean: str = remove_fixes(subject)

    # ID extrahieren
    quelle_id = link.split("/")[-1]

    # Eintrag erstellen
    return create_news_entry(
        link, subject_clean, date, text, locations, [], "Rundmail", quelle_id
    )


def main():
    # Rundmail-Archiv aufrufen und verarbeiten
    rundmail_archive: str = fetch_rundmail_archive()
    archive_entries: list[bs4.element.Tag] = parse_rundmail_archive(rundmail_archive)  # type: ignore
    news: list[dict] = []

    # Einträge im Archiv verarbeiten
    for archive_entry in archive_entries[:20]:
        entry: dict | list[dict] = process_archive_entry(archive_entry)
        if isinstance(entry, dict):
            news.append(entry)
        else:
            news.extend(entry)

    # Einträge in JSON-Datei speichern (zum Testen)
    """ json_data = json.dumps(news, ensure_ascii=False)
    json_data_encoded = json_data.encode("utf-8")
    with open("rundmail.json", "wb") as file:
        file.write(json_data_encoded) """

    # Einträge an Frontend senden
    json_data: str = json.dumps(news, ensure_ascii=False)
    json_data_encoded: bytes = json_data.encode("utf-8")
    send_to_frontend.send_data(json_data_encoded)
