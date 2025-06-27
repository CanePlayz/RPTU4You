from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

import bs4
import requests
import scraper.util.frontend_interaction as frontend_interaction
from scraper.util.create_news_entry import create_news_entry
from scraper.util.save_as_json import save_as_json


def fetch_news_page() -> bs4.BeautifulSoup:
    # News-Seite des Fachbereichs aufrufen
    html_code = requests.get(
        "https://wiwi.rptu.de/aktuelles/aktuelles-und-mitteilungen"
    ).text
    return bs4.BeautifulSoup(html_code, "html.parser")


def get_aktuelles_articles(soup: bs4.BeautifulSoup) -> bs4.ResultSet[bs4.element.Tag]:
    # Aktuelles-Bereich in BeautifulSoup-Objekt umwandeln
    aktuelles = soup.find("div", {"id": "c16235"})

    # Artikel-Objekte aus dem Aktuelles-Bereich extrahieren
    if isinstance(aktuelles, bs4.element.Tag):
        articles = aktuelles.find_all("article")
        return cast(bs4.ResultSet[bs4.element.Tag], articles)
    else:
        return cast(bs4.ResultSet[bs4.element.Tag], [])


def get_science_articles(soup: bs4.BeautifulSoup) -> bs4.ResultSet[bs4.element.Tag]:
    # Science-Bereich in BeautifulSoup-Objekt umwandeln
    science = soup.find("div", {"id": "c26813"})

    # Artikel-Objekte aus dem Science-Bereich extrahieren
    if isinstance(science, bs4.element.Tag):
        articles = science.find_all("article")
        return cast(bs4.ResultSet[bs4.element.Tag], articles)
    else:
        return cast(bs4.ResultSet[bs4.element.Tag], [])


def get_next_page_aktuelles(soup: bs4.BeautifulSoup) -> bs4.BeautifulSoup:
    # Navigationsleiste mit Pagination-Links extrahieren
    nav = soup.find_all("ul", class_="f3-widget-paginator")[0]
    if isinstance(nav, bs4.element.Tag):
        # Button für nächste Seite extrahieren
        next_page_button = nav.find("li", class_="rptu-page-item last next")
        if isinstance(next_page_button, bs4.element.Tag):
            # Versuche, Link in dem Button zu finden
            try:
                link = next_page_button.find("a")
            # Kann kein Link gefunden werden, ist das Ende erreicht
            except:
                raise Exception
            else:
                if isinstance(link, bs4.element.Tag):
                    href = link.get("href")
                    complete_link = f"https://wiwi.rptu.de{href}"
                    html_code = requests.get(complete_link).text
                    return bs4.BeautifulSoup(html_code, "html.parser")

    # Falls kein valides Objekt gefunden wurde (nur für Type-Hints)
    return bs4.BeautifulSoup("", "html.parser")


def get_next_page_science(soup: bs4.BeautifulSoup) -> bs4.BeautifulSoup:
    # Navigationsleiste mit Pagination-Links extrahieren
    nav = soup.find_all("ul", class_="f3-widget-paginator")[1]
    if isinstance(nav, bs4.element.Tag):
        # Button für nächste Seite extrahieren
        next_page_button = nav.find("li", class_="rptu-page-item last next")
        if isinstance(next_page_button, bs4.element.Tag):
            # Versuche, Link in dem Button zu finden
            try:
                link = next_page_button.find("a")
            # Kann kein Link gefunden werden, ist das Ende erreicht
            except:
                raise Exception
            else:
                if isinstance(link, bs4.element.Tag):
                    href = link.get("href")
                    complete_link = f"https://wiwi.rptu.de{href}"
                    html_code = requests.get(complete_link).text
                    return bs4.BeautifulSoup(html_code, "html.parser")

    # Falls kein valides Objekt gefunden wurde (nur für Type-Hints)
    return bs4.BeautifulSoup("", "html.parser")


def process_entry(entry: bs4.element.Tag, science: bool) -> dict | list[dict]:
    # Link extrahieren
    a_element = entry.find("a")
    if isinstance(a_element, bs4.element.Tag):
        href = a_element.get("href")
        complete_link: str = f"https://wiwi.rptu.de{href}"

    # Titel extrahieren
    if isinstance(a_element, bs4.element.Tag):
        title_attribute = a_element.get("title")
        if isinstance(title_attribute, str):
            title = title_attribute

    # Datum extrahieren
    time_element = entry.find("time")
    if isinstance(time_element, bs4.element.Tag):
        time_string = time_element.get("datetime")
        if isinstance(time_string, str):
            date_object: datetime = datetime.strptime(time_string, "%Y-%m-%d")
            date: datetime = date_object.replace(tzinfo=ZoneInfo("Europe/Berlin"))

    # Kategorien festlegen
    if science:
        categories = ["Studierende", "Veranstaltungen"]
    else:
        categories = ["Studierende", "Mitarbeitende"]

    # Eintrag aufrufen und in BeautifulSoup-Objekt umwandeln
    news_entry_html: str = requests.get(complete_link).text
    news_entry_soup: bs4.BeautifulSoup = bs4.BeautifulSoup(
        news_entry_html, "html.parser"
    )

    # Text scrapen
    text_div = news_entry_soup.find("div", class_="news-content")
    if isinstance(text_div, bs4.element.Tag):
        p_elements = text_div.find_all("p")
        text = ""
        if isinstance(p_elements, bs4.ResultSet):
            for p in p_elements:
                if isinstance(p, bs4.element.Tag):
                    text += p.get_text() + "<br><br>"

    return create_news_entry(
        complete_link,
        title,
        date,
        text,
        ["Kaiserslautern"],
        categories,
        "Fachschaft",
        "Fachbereich Wirtschaftswissenschaften",
    )


def main():
    news = []

    # News-Seite vom Fachbereich aufrufen
    soup: bs4.BeautifulSoup = fetch_news_page()

    # Aktuelles-Artikel scrapen
    aktuelles_articles = []
    while True:
        aktuelles_articles += get_aktuelles_articles(soup)
        try:
            new_page = get_next_page_aktuelles(soup)
        except:
            break
        else:
            soup = new_page

    for article in aktuelles_articles:
        news.append(process_entry(article, False))

    # News-Seite vom Fachbereich aufrufen
    soup: bs4.BeautifulSoup = fetch_news_page()

    # Science-Artikel scrapen
    science_articles = []
    while True:
        science_articles += get_science_articles(soup)
        try:
            new_page = get_next_page_science(soup)
        except:
            break
        else:
            soup = new_page

    for article in science_articles:
        news.append(process_entry(article, True))

    # Einträge in JSON-Datei speichern (zum Testen)
    # save_as_json(news, "wiwi_news")

    frontend_interaction.send_data(news, "Wiwi-Scraper")
