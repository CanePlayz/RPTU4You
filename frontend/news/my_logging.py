import logging


def get_logger(name: str) -> logging.Logger:
    """Im Django-Container übernimmt Django die Logging-Konfiguration."""
    return logging.getLogger(name)
