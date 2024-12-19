import requests


def send_to_frontend(data):
    response = requests.post(
        "http://django:8000/api/news",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    print(response.status_code, response.text)
