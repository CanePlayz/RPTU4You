import time
from datetime import datetime

import bs4
import requests
import scraper.util.frontend_interaction as frontend_interaction
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    # options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver: webdriver.Chrome = webdriver.Chrome(
        options=options,
    )

    return driver


def unfold_news(driver: webdriver.Chrome) -> None:
    while True:
        button = driver.find_element(By.CSS_SELECTOR, ".reload-news-records")
        classes = button.get_attribute("class")
        if classes:
            # Überprüfe, ob der Button noch sichtbar ist
            if "d-none" in classes:
                break
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", button
            )
            time.sleep(1)
            button.click()
            time.sleep(1)


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


def process_article(relative_link: str) -> dict:
    link = "https://rptu.de" + relative_link
    page = bs4.BeautifulSoup(requests.get(link).text, "html.parser")

    # Titel extrahieren
    title_element = page.find("h1")
    if isinstance(title_element, bs4.Tag):
        title: str = title_element.text

    # Datum extrahieren
    time_element = page.find("time")
    if isinstance(time_element, bs4.Tag):
        time_string = time_element.get("datetime")
        if isinstance(time_string, str):
            date: datetime = datetime.strptime(time_string, "%Y-%m-%d")

    # Text extrahieren
    text: str = ""

    news_content_div = page.find("div", class_="news-content")
    if isinstance(news_content_div, bs4.Tag):
        direct_children: bs4.ResultSet = news_content_div.find_all(
            recursive=False,
        )
        text_children = direct_children[2:]

        for child in text_children:
            if isinstance(child, bs4.Tag):

                if child.name == "p":
                    text += child.decode_contents() + "<br><br>"

                elif child.name == "ul":
                    text += child.decode_contents() + "<br>"

    locations = []
    categories = []
    source_type = "Interne Website"
    source_name = "RPTU Newsroom"

    return create_news_entry(
        link,
        title,
        date,
        text,
        locations,
        categories,
        source_type,
        source_name,
    )


def main():
    driver = setup_driver()
    driver.get("https://rptu.de/newsroom/pressemitteilungen")
    unfold_news(driver)

    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(driver.page_source, "html.parser")
    articles: bs4.ResultSet = soup.find_all(
        "div",
        class_="news-item",
    )

    driver.quit()

    news = []

    for article in articles:
        a_element: bs4.Tag = article.find("a")
        if isinstance(a_element, bs4.Tag):
            link = a_element.get("href")
            if isinstance(link, str):
                news.append(process_article(link))

    # Einträge in JSON-Datei speichern (zum Testen)
    """ for entry in news:
        entry["text"] = entry["text"].replace('"', "'")
    json_data = json.dumps(
        news, ensure_ascii=False, default=frontend_interaction.datetime_serializer
    )
    json_data_encoded = json_data.encode("utf-8")
    with open("rundmail.json", "wb") as file:
        file.write(json_data_encoded)
    """

    # Einträge an Frontend senden
    frontend_interaction.send_data(news, "Newsroom-Scraper")
