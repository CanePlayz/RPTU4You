import requests


def send_to_frontend(data):
    response = requests.post(
        "http://django:8000/api/news",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "API-Key": "0jdf3wfjq98w3jdf9w8",
        },
    )
    print(response.status_code, response.text)
