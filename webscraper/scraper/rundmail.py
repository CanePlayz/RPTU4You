import json

import bs4
import requests
from util import send_to_frontend


def remove_fixes(subject: str) -> str:
    replacements = [
        "[Mitarbeitende] ",
        "[Studierende] ",
        " #KL",
        " #LD",
    ]
    for r in replacements:
        subject_clean = subject.replace(r, "")
    return subject_clean


def clean_text(text: str) -> str:
    # Entferne Escape-Sequenzen
    text = text.replace("\\r\\n", "<br>")
    # Ersetze HTML-Tags durch ihre entsprechenden Zeichen
    text = text.replace('\\"', '"')
    return text


def main():
    rundmail_archiv = requests.get("https://rundmail.rptu.de/archive").text
    news: list[dict] = []
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(rundmail_archiv, "html.parser")

    # Alle Tabellenzeilen finden
    news_einträge = soup.find_all(name="tr")[0:]

    # Durch alle Einträge im Archiv iterieren
    for archiv_eintrag in news_einträge[1:20]:
        link = f"https://rundmail.rptu.de{archiv_eintrag.find(name="a").get("href")}"
        eintrag_html = requests.get(link).text
        eintrag_soup = bs4.BeautifulSoup(eintrag_html, "html.parser")

        # Datum von Eintrag finden
        datum = archiv_eintrag.find(name="td", class_="created_at").text.strip()

        # Subject von Eintrag finden und prüfen, ob es sich um eine Rundmail handelt
        subject: str = archiv_eintrag.find(name="td", class_="subject").text

        # Sammel-Rundmail
        if subject.startswith("Sammel-Rundmail"):
            messages_overview = eintrag_soup.find(
                name="div", class_="messages-overview"
            )
            if isinstance(messages_overview, bs4.element.Tag):
                kategorien = messages_overview.find_all(name="h5", class_="mt-4")
            else:
                kategorien = []
            for kategorie in kategorien:
                kategorie_name = kategorie.text
                kategorie_einträge = kategorie.find_next_sibling(name="ul").find_all(
                    name="li"
                )

                for kategorie_eintrag in kategorie_einträge:
                    a_element: bs4.element.Tag = kategorie_eintrag.find(name="a")
                    if isinstance(a_element, bs4.element.Tag):
                        subject = a_element.text
                        eintrag_id = a_element.get("href")
                        if isinstance(eintrag_id, str):
                            eintrag_id = eintrag_id.replace("#", "")

                    heading_eintrag = eintrag_soup.find(name="h2", id=eintrag_id)
                    if isinstance(heading_eintrag, bs4.element.Tag):
                        accordion_body = heading_eintrag.find_next_sibling(name="div")
                        if isinstance(accordion_body, bs4.element.Tag):
                            text = accordion_body.find(name="p", class_="whitespaces")
                            if isinstance(text, bs4.element.Tag):
                                text = text.decode_contents()

                    # Standorte aus Subject extrahieren
                    if subject.endswith("#KL"):
                        standorte = ["Kaiserslautern"]
                    elif subject.endswith("#LD"):
                        standorte = ["Landau"]
                    else:
                        standorte = ["Kaiserslautern", "Landau"]

                    kategorien = []
                    if subject.startswith("[Mitarbeitende]"):
                        kategorien.append("Mitarbeitende")
                    if subject.startswith("[Studierende]"):
                        kategorien.append("Studierende")

                    if kategorie_name == "Veranstaltungen":
                        kategorien.append("Veranstaltung")
                    elif kategorie_name == "Umfragen":
                        kategorien.append("Umfrage")

                    # Präfixe und Suffixe entfernen
                    subject_clean = remove_fixes(subject)

                    # Eintrag erstellen
                    eintrag = {
                        "link": f"{link}#{eintrag_id}",
                        "titel": subject_clean,
                        "erstellungsdatum": datum,
                        "text": text,
                        "standorte": standorte,
                        "kategorien": kategorien,
                        "quelle": "Sammel-Rundmail",
                    }

                    news.append(eintrag)

        # Rundmail
        else:
            # p-Element mit Text finden
            text_element = eintrag_soup.find(name="p", class_="whitespaces")

            # Text aus p-Element extrahieren
            if isinstance(text_element, bs4.element.Tag):
                text = text_element.decode_contents()
            else:
                exit()

            # Standorte aus Subject extrahieren
            if subject.endswith("#KL"):  #
                standorte = ["Kaiserslautern"]
            elif subject.endswith("#LD"):
                standorte = ["Landau"]
            else:
                standorte = ["Kaiserslautern", "Landau"]

            # Präfixe und Suffixe entfernen
            subject_clean = remove_fixes(subject)

            # Eintrag erstellen
            eintrag = {
                "link": link,
                "titel": subject,
                "erstellungsdatum": datum,
                "text": text,
                "standorte": standorte,
                "kategorien": [],
                "quelle": "Rundmail",
            }
            news.append(eintrag)

    # JSON-Daten erstellen
    json_data = clean_text(json.dumps(news, ensure_ascii=False))
    json_data = json_data.encode("utf-8")

    # POST-Anfrage an Frontend senden
    # send_to_frontend.send_to_frontend(json_data)


main()
