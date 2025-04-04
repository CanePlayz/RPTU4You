from bs4.element import NavigableString
from deep_translator import GoogleTranslator


def translate_html(soup, from_lang, to_lang):
    for elem in soup.contents:
        if isinstance(elem, NavigableString):
            # NavigableString-Elemente sind nur Text, also übersetzen
            translated_text = GoogleTranslator(
                source=from_lang, target=to_lang
            ).translate(str(elem))
            if translated_text:
                # Übersetzten Text ersetzen
                elem.replace_with(NavigableString(translated_text))
        elif elem.name is not None:
            # Rekursiv Elemente nach Text durchsuchen
            translate_html(elem, from_lang, to_lang)
