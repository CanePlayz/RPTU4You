import time
from datetime import date, datetime

import scraper.fachbereiche.wiwi as wiwi
import scraper.newsroom.pressemitteilungen as pressemitteilungen
import scraper.rundmail as rundmail
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger


def main():
    scheduler = BlockingScheduler()

    time.sleep(15)  # Django benötigt etwas Zeit, um zu starten

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

    print("Scheduler läuft...")
    scheduler.start()


if __name__ == "__main__":
    main()
