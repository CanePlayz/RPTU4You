import bs4
import requests


def main():
    rundmail_archiv = requests.get("https://rundmail.rptu.de/archive").text
    news: list[dict] = []
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(rundmail_archiv, "html.parser")

    # Alle Tabellenzeilen finden
    news_einträge = soup.find_all(name="tr")[0:]

    for archiv_eintrag in news_einträge[1:10]:
        link = f"https://rundmail.rptu.de/{archiv_eintrag.find(name="a").get("href")}"
        eintrag_html = requests.get(link).text
        eintrag_soup = bs4.BeautifulSoup(eintrag_html, "html.parser")

        # Datum von Eintrag finden
        datum = archiv_eintrag.find(name="td", class_="created_at").text.strip()
        print(datum)

        # Subject von Eintrag finden und prüfen, ob es sich um eine Rundmail handelt
        subject = archiv_eintrag.find(name="td", class_="subject").text
        if subject.startswith("Sammel-Rundmail"):
            print("Rundmail")
        else:
            print("Keine Rundmail")
            # Div mit Text finden
            text = eintrag_soup.find(name="p", class_="whitespaces")

            eintrag = {
                "link": link,
                "titel": subject,
                "erstellungsdatum": datum,
                "text": text,
            }
            news.append(eintrag)
    print(news)


main()
