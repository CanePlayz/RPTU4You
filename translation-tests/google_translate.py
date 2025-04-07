from bs4 import BeautifulSoup
from bs4.element import NavigableString
from deep_translator import GoogleTranslator


def translate_html(soup, from_lang="de", to_lang="en"):
    for elem in soup.contents:
        if isinstance(elem, NavigableString):
            # NavigableString-Elemente sind nur Text, also übersetzen
            translated_text = GoogleTranslator(source="de", target="en").translate(
                str(elem)
            )
            if translated_text:
                # Übersetzten Text ersetzen
                elem.replace_with(NavigableString(translated_text))
        elif elem.name is not None:
            # Rekursiv Elemente nach Text durchsuchen
            translate_html(elem, from_lang, to_lang)


# Beispiel HTML
with open("translation-tests\\original_text.txt", "r", encoding="utf-8") as f:
    text = f.read()

soup = BeautifulSoup(text, "html.parser")

translate_html(soup)

with open("translation-tests\\translated_text_google.txt", "w", encoding="utf-8") as f:
    f.write(str(soup))
