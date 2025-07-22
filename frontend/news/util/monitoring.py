import logging
import threading
import time

from django.db import connection


def log_open_db_connections():
    logger = logging.getLogger("db_monitor")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database();"
        )
        result = cursor.fetchone()
        count = result[0] if result is not None else 0
        logger.info(f"[DB-Monitor] Aktive DB-Verbindungen: {count}")


def start_monitoring():
    def monitor():
        while True:
            log_open_db_connections()
            time.sleep(0.01)

    threading.Thread(target=monitor, daemon=True).start()
