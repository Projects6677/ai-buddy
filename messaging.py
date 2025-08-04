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
    # --- MODIFICATION START ---
    # Changed language code to "en_IN" to match your Indian English template
    template_data = {
        "name": template_name,
        "language": {"code": "en_IN"}
    }
    # --- MODIFICATION END ---
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

def send_interactive_menu(to, name):
    """Sends the main interactive list menu."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    welcome_text = f"👋 Welcome back, *{name}*!\n\nHow can I assist you today?"

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "AI Buddy Menu 🤖"
            },
            "body": {
                "text": welcome_text
            },
            "footer": {
                "text": "Please select an option"
            },
            "action": {
                "button": "Choose an Option",
                "sections": [
                    {
                        "title": "Main Features",
                        "rows": [
                            {"id": "1", "title": "Set a Reminder", "description": "Schedule a reminder for any task."},
                            {"id": "2", "title": "Fix Grammar", "description": "Correct spelling and grammar."},
                            {"id": "3", "title": "Ask AI Anything", "description": "Chat with the AI assistant."},
                            {"id": "4", "title": "File/Text Conversion", "description": "Convert between PDF and Word."},
                            {"id": "5", "title": "Translator", "description": "Translate text between languages."},
                            {"id": "6", "title": "Weather Forecast", "description": "Get the current weather."},
                            {"id": "7", "title": "Currency Converter", "description": "Convert between currencies."},
                            {"id": "8", "title": "AI Email Assistant", "description": "Get help writing professional emails."}
                        ]
                    }
                ]
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send interactive menu to {to}: {e.response.text if e.response else e}")
