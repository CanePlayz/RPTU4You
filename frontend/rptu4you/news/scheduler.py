from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .translate_articles.translate_news_articles import translate_news_articles


def start():
    translate_news_articles()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        translate_news_articles,
        trigger=IntervalTrigger(hours=1),
        id="translate_news_articles_job",
        name="Übersetzung der Artikel",
        replace_existing=True,
    )
    scheduler.start()
