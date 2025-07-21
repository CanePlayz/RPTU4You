import logging
import sys


def get_logger_django(name: str) -> logging.Logger:
    """Im Django-Container übernimmt Django die Logging-Konfiguration."""
    return logging.getLogger(name)


def get_logger_scraper(name: str) -> logging.Logger:
    """Im Scraper-Container wird das Logging manuell konfiguriert."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Unerwünschte Logger deaktivieren
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

    return logging.getLogger(name)
