import os
import subprocess

# PowerShell-Befehl, um PYTHONPATH zu setzen, damit die Imports aus common funktionieren
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

ps_command = f'$env:PYTHONPATH="{project_root}"'

# Subprozess starten
subprocess.run(["pwsh", "-Command", ps_command], check=True)

import scraper.fachbereiche.wiwi as wiwi
import scraper.mail.mail_scraper as mail_scraper
import scraper.newsroom.pressemitteilungen as pressemitteilungen
import scraper.rundmail.rundmail as rundmail
from dotenv import load_dotenv


def main():
    load_dotenv(os.path.join(project_root, ".env"))

    # wiwi.main()
    mail_scraper.main()
    # pressemitteilungen.main()
    # rundmail.main()


if __name__ == "__main__":
    main()
