import requests
import os

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN") or "EAAJ0jnn2gyMBO0wSo7dZCIVnceSx0AapQ7IWvL1MOggG6jEXVR4pi7Gqtjbgvbi2AgWWvNb7fPs9TQCRgZA32a13OrARh0ZBZBNKrcQkv7ZBZAHHtU7ddINVue9M6WJHjbg0zZCj9M6lDPMvRrfyu6ZAsuzZByIioeGfvxRzMQ9BHlCT8c2B5gvh6cjIs4Go5vZAilbH5blsGeUZAlgWVdnC9dvsUNgBuJ7ODvrBMXzXZBGtnZALf28UZD"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") or "698497970011796"

def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    requests.post(url, headers=headers, json=data)
