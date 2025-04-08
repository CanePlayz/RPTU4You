from pydoc import text

from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from rptu4you.news.models import News, Sprache, Text

from .util import translate_html


def translate_news_articles():
    sprachen = Sprache.objects.exclude(name="Deutsch")
    news_items = News.objects.all()

    for news in news_items:
        print("News-Objekt:", news.titel)
        for sprache in sprachen:
            print("Sprache:", sprache.name)

            if not Text.objects.filter(news=news, sprache=sprache).exists():
                print("Übersetzung nötig.")

                # Übersetzung des Titels
                try:
                    translated_title = GoogleTranslator(
                        source="de", target=sprache.code
                    ).translate(news.titel)
                except Exception as e:
                    print(f"Fehler bei der Übersetzung des Titels für {sprache}: {e}")
                    translated_title = None
                else:
                    print("Übersetzter Titel:", translated_title)

                # Übersetzung des Textes
                try:
                    original_text_de = Text.objects.get(
                        news=news, sprache__name="Deutsch"
                    ).text
                    soup = BeautifulSoup(original_text_de, "html.parser")
                    translate_html.translate_html(
                        soup, from_lang="de", to_lang=sprache.code
                    )
                    Text.objects.create(
                        news=news,
                        text=str(soup),
                        titel=translated_title,
                        sprache=sprache,
                    )
                except Exception as e:
                    print(f"Fehler bei der Übersetzung für {sprache}: {e}")
                else:
                    print("Übersetzter Text:", str(soup))
                print("Übersetzung erfolgreich.")
                print()

            else:
                print("Übersetzung bereits vorhanden.")
                print()
