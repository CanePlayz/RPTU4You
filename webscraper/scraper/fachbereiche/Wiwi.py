from datetime import datetime

import bs4
import requests
import scraper.util.frontend_interaction as frontend_interaction

def clean_text(text: str) -> str:
    # Unicode-Zeichen für Zeilenumbrüche entfernen
    text_processed: str = text.replace("\\r\\n", "<br>")
    # Escaping von Anführungszeichen entfernen
    text_processed: str = text.replace('\\"', '"')
    return text_processed

def create_news_entry(
    link: str,
    title: str,
    date: datetime,
    text: str,
    locations: list,
    categories: list[str],
    source_type: str,
    source_name: str,
) -> dict:

    return {
        "link": link,
        "titel": title,
        "erstellungsdatum": date,
        "text": text,
        "standorte": locations,
        "kategorien": categories,
        "quelle_typ": source_type,
        "quelle_name": source_name,
    }

def fetch_oberseite() -> str:
    # News Seite des Fachbereichs aufrufen
    return requests.get("https://wiwi.rptu.de/aktuelles/aktuelles-und-mitteilungen").text

def change_page(page:str) -> str:
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(page, "html.parser")
    #Navigationsleiste zum Seiten ändern bekommen
    aktuelles_change = soup.find("ul",class_="f3-widget-paginator")
    next_page = aktuelles_change.find("li",class_="rptu-page-item last next")
    link = next_page.find("a")
    href = link.get("href")
    complete_link = f"https://wiwi.rptu.de{href}"
    return requests.get(complete_link).text


def parse_aktuelles_articles(html: str) -> list[bs4.element.Tag]:
    # News Seite in BeautifulSoup-Objekt umwandeln
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html, "html.parser")
    aktuelles = soup.find("div", {"id" : "c16235"})
    articles = aktuelles.find_all("article")
    return articles  # type: ignore

def parse_science_articles(html:str, first_scraped: bool) -> list[bs4.element.Tag]:
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html, "html.parser")
    if first_scraped:
        science = soup.find("div", {"id" : "c26813"})
        articles = science.find_all("articles")
    else:
        #Entferne Dekanatsnachrichten, stehen unter Aktuelles
        remove_dekanat = soup.find("div", {"id" : "c19997"}).extract()
        remove_aktuelles = soup.find("div", {"id" : "c16235"}).extract()
        articles = soup.find_all("articles")
    return articles

def process_entry(entry:bs4.element.Tag, science: bool) -> dict | list[dict]:
    # Link zu News extrahieren
    link = entry.find("a")
    if isinstance(link, bs4.element.Tag):
        href = link.get("href")
    complete_link: str = f"https://wiwi.rptu.de{href}"
    #Titel, Datum, location, Source, Sourcename und Kategorien  definieren
    title: str = link.get("title")
    time = entry.find("time")
    if isinstance(time, bs4.Tag):
        time_string = time.get("datetime")
        if isinstance(time_string, str):
            date: datetime = datetime.strptime(time_string, "%Y-%m-%d")
    if science:
        categories = ["Studierende", "Veranstaltungen"]
    else:
        categories = ["Studierende", "Mitarbeitende"]


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
    clean_text = clean_text(text)

    return create_news_entry(complete_link,title,date,clean_text,"Kaiserslautern",categories,"Fachschaft", "Fachbereich Wirtschaftswissenschaften")
    
def main():
    #Webseite aufrufen
    wiwi = []
    count = 0
    fachbereich = fetch_oberseite()
    aktuelles = parse_aktuelles_articles(fachbereich)
    for artikel in aktuelles:
        entry = process_entry(artikel,False)
        wiwi.append(entry)
    science = parse_science_articles(fachbereich,False)
    for i in science:
        entry = process_entry(i,True)
        wiwi.append(entry)
    for i in range(5):
        new_page = change_page(fachbereich)
        next_articles = parse_aktuelles_articles(new_page)
        for article in next_articles:
            wiwi.append(process_entry(article,False))
        if count <= 4:
            next_science = parse_science_articles(new_page,True)
            for science in next_science:
                wiwi.append(process_entry(science,True))
            count += 1
    frontend_interaction.send_data(wiwi, "WiwiScraper")






    
