import scraper.newsroom.pressemitteilungen as pressemitteilungen
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
        func=pressemitteilungen.main,
        trigger=IntervalTrigger(minutes=1),
        id="newsroom_job",
        name="Newsroom-Scraper",
        replace_existing=True,
    )

    print("Scheduler läuft...")
    scheduler.start()


if __name__ == "__main__":
    main()
