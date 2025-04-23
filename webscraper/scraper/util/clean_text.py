def clean_text(text: str) -> str:
    # Unicode-Zeichen für Zeilenumbrüche entfernen
    text_processed: str = text.replace("\\r\\n", "<br>")
    # Escaping von Anführungszeichen entfernen
    text_processed: str = text.replace('\\"', '"')

    return text_processed
