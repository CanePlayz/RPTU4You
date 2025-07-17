import os
import time
from datetime import datetime
from pickletools import read_unicodestring1
from zoneinfo import ZoneInfo

import bs4
import requests
import scraper.util.frontend_interaction as frontend_interaction
from scraper.util.create_news_entry import create_news_entry
from scraper.util.save_as_json import save_as_json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait


def setup_driver() -> webdriver.Firefox:
    options = Options()

    # Headless-Modus aktivieren
    options.add_argument("--headless")

    # Logging deaktivieren
    os.environ["MOZ_LOG"] = "error"

    # Setze den Pfad zum Firefox-Binary und zum Geckodriver
    options.binary_location = "/usr/bin/firefox"
    service = Service(executable_path="/usr/local/bin/geckodriver")

    driver: webdriver.Firefox = webdriver.Firefox(
        options=options,
        service=service,
    )

    return driver


def unfold_news(driver: webdriver.Firefox) -> None:
    while True:
        # Anzahl der News-Artikel vor dem Klicken des Buttons
        items = driver.find_elements(By.CSS_SELECTOR, ".news-item")
        items_count = len(items)

        # Klicke den Button, um weitere News zu laden
        button = driver.find_element(By.CSS_SELECTOR, ".reload-news-records")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        time.sleep(2)
        button.click()
        time.sleep(2)

        # Überprüfe, ob der Button noch weitere News geladen hat
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, ".news-item"))
                > items_count
            )
        except:
            break


def process_article(relative_link: str) -> dict:
    link = "https://rptu.de" + relative_link
    page = bs4.BeautifulSoup(requests.get(link).text, "html.parser")

    # Titel extrahieren
    title_element = page.find("h1")
    if not isinstance(title_element, bs4.Tag):
        return {}

    title: str = title_element.text

    # Datum extrahieren
    time_element = page.find("time")
    if not isinstance(time_element, bs4.Tag):
        return {}

    time_string = time_element.get("datetime")
    if not isinstance(time_string, str):
        return {}

    date_object: datetime = datetime.strptime(time_string, "%Y-%m-%d")
    date: datetime = date_object.replace(tzinfo=ZoneInfo("Europe/Berlin"))

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
    source_type = "Interne Website"
    source_name = "RPTU Newsroom"

    return create_news_entry(
        link, title, date, text, locations, source_type, source_name
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
    # save_as_json(news, "pressemitteilungen")

    # Einträge an Frontend senden
    frontend_interaction.send_data(news, "Newsroom-Scraper")
