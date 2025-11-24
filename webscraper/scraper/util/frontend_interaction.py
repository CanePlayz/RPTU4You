import gzip
import json
import os
from datetime import datetime
from math import ceil
from typing import Iterable, Sequence

import requests

from .my_logging import get_logger

logger = get_logger(__name__)


def datetime_serializer(obj) -> str:
    """Datums-Objekte in ein serialisierbares Format umwandeln."""
    if isinstance(obj, datetime):
        return obj.strftime("%d.%m.%Y %H:%M:%S")
    raise TypeError("Type not serializable")


def _chunk_payload(payload: Sequence, batch_size: int) -> Iterable[Sequence]:
    """Teilt die Nutzlast in kleinere Batches auf."""
    for start in range(0, len(payload), batch_size):
        yield payload[start : start + batch_size]


def _post_chunk(chunk, api_key: str, source_type: str) -> int:
    """Ein Daten-Chunk an das Frontend senden."""
    json_data = json.dumps(chunk, default=datetime_serializer)
    compressed_data = gzip.compress(json_data.encode("utf-8"))
    response = requests.post(
        "http://django:8000/api/news/",
        data=compressed_data,
        headers={
            "Content-Encoding": "gzip",
            "Content-Type": "application/json; charset=utf-8",
            "API-Key": api_key,
        },
    )
    logger.info(f"{source_type} - Status Code: {response.status_code}")
    return response.status_code


def send_data(data, source_type: str, batch_size: int):
    """Daten an das Frontend senden, ggf. in Batches aufgeteilt."""
    api_key = os.getenv("API_KEY", "")
    batch_size = int(os.getenv("SCRAPER_BATCH_SIZE", 25))

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        total_items = len(data)
        if total_items > batch_size:
            total_batches = ceil(total_items / batch_size)
            for index, chunk in enumerate(_chunk_payload(data, batch_size), start=1):
                logger.info(
                    f"{source_type} - Sende Batch {index}/{total_batches} ({len(chunk)} Einträge)"
                )
                _post_chunk(chunk, api_key, source_type)
            logger.info(
                f"{source_type} - Fertig: {total_items} Einträge in {total_batches} Batches gesendet"
            )
            return

    _post_chunk(data, api_key, source_type)
