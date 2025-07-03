# Suche nach Sprachblöcken
import re

chatgpt_response = ""

match_de = re.search(
    r"\[LANGUAGE:de\]\s*(.*?)\s*(?=\[LANGUAGE:|$)", chatgpt_response, re.DOTALL
)
match_en = re.search(
    r"\[LANGUAGE:en\]\s*(.*?)\s*(?=\[LANGUAGE:|$)", chatgpt_response, re.DOTALL
)

# boolesche Variablen
has_de = match_de is not None
has_en = match_en is not None
has_both = has_de and has_en

# Extrahierte Inhalte
de_text = match_de.group(1).strip() if has_de else ""
en_text = match_en.group(1).strip() if has_en else ""
