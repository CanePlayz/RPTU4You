import gzip
import json
import os
from datetime import datetime

import requests


def datetime_serializer(obj) -> str:
    if isinstance(obj, datetime):
        return obj.strftime("%d.%m.%Y %H:%M:%S")
    raise TypeError("Type not serializable")


def request_date():
    api_key = os.getenv("API_KEY")
    response = requests.get(
        "http://django:8000/api/news/rundmail/date",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "API-Key": api_key,
        },
    )

    if response.status_code == 200:
        # JSON-Daten aus dem Response-Body laden
        data = response.json()
        date = data["date"]
        date_object: datetime = datetime.strptime(date, "%d.%m.%Y %H:%M:%S")

        return date_object
    else:
        print("Fehler beim Abrufen des Datums:", response.status_code, response.text)
        return None


def send_data(data, type):
    api_key = os.getenv("API_KEY")
    json_data = json.dumps(data, default=datetime_serializer)
    compressed_data = gzip.compress(json_data.encode("utf-8"))
    response = requests.post(
        "http://django:8000/api/news",
        data=compressed_data,
        headers={
            "Content-Encoding": "gzip",
            "Content-Type": "application/json; charset=utf-8",
            "API-Key": api_key,
        },
    )
    print(f"{type} - Status Code: {response.status_code}")
