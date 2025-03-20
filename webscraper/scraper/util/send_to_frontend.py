import os

import requests


def send_data(data):
    api_key = os.getenv("API_KEY")
    response = requests.post(
        "http://django:8000/api/news",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "API-Key": api_key,
        },
    )
    print(response.status_code, response.text)
