# messaging.py
import requests
import os

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def send_message(to, message):
    """Sends a standard text message."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message, "preview_url": True}
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to {to}: {e}")


def send_template_message(to, template_name, components=[]):
    """Sends a pre-approved template message."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    template_data = {
        "name": template_name,
        "language": {"code": "en_US"} # Using en_US for better compatibility
    }
    if components:
        template_data["components"] = components
        
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template_data
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        print(f"Template '{template_name}' sent to {to}. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send template message to {to}: {e.response.text if e.response else e}")
