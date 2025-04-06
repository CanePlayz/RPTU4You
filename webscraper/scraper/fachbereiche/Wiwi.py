from datetime import datetime

import bs4
import requests
import scraper.util.frontend_interaction as frontend_interaction


def fetch_oberseite() -> str:
    # News Seite des Fachbereichs aufrufen
    return requests.get("https://wiwi.rptu.de/aktuelles/aktuelles-und-mitteilungen").text

def parse_first_articles(html: str) -> list[bs4.element.Tag]:
    # News Seite in BeautifulSoup-Objekt umwandeln
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html, "html.parser")
    # Alle Einträge der Seite extrahieren
    return soup.find_all(name="article")  # type: ignore

def process_entry(entry:bs4.element.Tag) -> dict | list[dict]:
    # Link zu News extrahieren
    link = entry.find(name="a")
    if isinstance(link, bs4.element.Tag):
        href = link.get("href")
    complete_link: str = f"https://wiwi.rptu.de{href}"
    #Titel, Datum, location, Source und Source name schonmal aufschreiben
    title: str = link.get("title")
    time = entry.find(name="time")
    if isinstance(time, bs4.Tag):
        time_string = time.get("datetime")
        if isinstance(time_string, str):
            date: datetime = datetime.strptime(time_string, "%Y-%m-%d")
    location = "Kaiserslautern"
    source = "Fachschaft"
    source_type = "Fachbereich Wirtschaftswissenschaften"


    # Eintrag aufrufen und in BeautifulSoup-Objekt umwandeln
    news_entry_html: str = requests.get(complete_link).text
    news_entry_soup: bs4.BeautifulSoup = bs4.BeautifulSoup(
        news_entry_html, "html.parser"
    )
    #Text scrapen
    text_div = news_entry_soup.find("div", class_="col-12 col-lg-8 news-content")
    unwanted = text_div.find("div")
    unwanted.extract()
    text = text_div.text