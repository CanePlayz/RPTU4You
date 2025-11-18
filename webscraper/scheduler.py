import os
import time
from datetime import datetime

import requests
import scraper.fachbereiche.wiwi as wiwi
import scraper.mail.mail_scraper as mail_scraper
import scraper.newsroom.pressemitteilungen as pressemitteilungen
import scraper.rundmail.rundmail as rundmail
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from scraper.util.my_logging import get_logger

logger = get_logger(__name__)


def scrapers_disabled():
    value = os.getenv("DISABLE_SCRAPERS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def wait_for_django():
    django_url = "http://django:8000/health"
    for _ in range(60):
        try:
            response = requests.get(django_url)
            if response.status_code == 200:
                logger.info("Django ist bereit.")
                return
        except requests.ConnectionError:
            pass
        logger.info("Warte auf Django...")
        time.sleep(1)
    raise RuntimeError("Django konnte nicht gestartet werden.")


def main():
    if scrapers_disabled():
        logger.info("Scraper sind deaktiviert. Beende Scheduler.")
        return

    scheduler = BlockingScheduler()

    wait_for_django()  # Warte auf Django, bevor der Scheduler startet

    scheduler.add_job(
        func=rundmail.main,
        trigger=IntervalTrigger(minutes=20),
        id="rundmail_job",
        name="Rundmail-Scraper",
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        func=pressemitteilungen.main,
        trigger=IntervalTrigger(minutes=20),
        id="newsroom_job_1",
        name="Newsroom-Scraper (Pressmitteilungen)",
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        func=wiwi.main,
        trigger=IntervalTrigger(minutes=20),
        id="fachbereiche_job_wiwi",
        name="Fachbereiche-Scraper (Wiwi)",
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        func=mail_scraper.main,
        trigger=IntervalTrigger(minutes=20),
        id="mail_job",
        name="Mail-Scraper",
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    logger.info("Scheduler läuft...")
    scheduler.start()


if __name__ == "__main__":
    main()
