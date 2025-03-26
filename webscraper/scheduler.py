import scraper.presse as presse
import scraper.rundmail as rundmail
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger


def main():
    scheduler = BlockingScheduler()

    scheduler.add_job(
        func=rundmail.main,
        trigger=IntervalTrigger(minutes=1),
        id="rundmail_job",
        name="Rundmail-Scraper",
        replace_existing=True,
    )

    scheduler.add_job(
        func=presse.main,
        trigger=IntervalTrigger(minutes=1),
        id="presse_job",
        name="Presse-Scraper",
        replace_existing=True,
    )

    print("Scheduler läuft...")
    scheduler.start()


if __name__ == "__main__":
    main()
