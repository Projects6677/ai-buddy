# messaging.py
import requests
import os
import time

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
        "language": {"code": "en_US"}
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
            "header": {"type": "text", "text": "AI Buddy Menu 🤖"},
            "body": {"text": welcome_text},
            "footer": {"text": "Please select an option"},
            "action": {
                "button": "Choose an Option",
                "sections": [{"title": "Main Features","rows": [
                            {"id": "1", "title": "Set a Reminder", "description": "Schedule a one-time or recurring reminder."},
                            {"id": "reminders_check", "title": "Check Reminders", "description": "See all your active reminders."},
                            {"id": "2", "title": "Fix Grammar", "description": "Correct spelling and grammar."},
                            {"id": "3", "title": "Ask AI Anything", "description": "Chat with the AI assistant."},
                            {"id": "4", "title": "File/Text Conversion", "description": "Convert between PDF and Word."},
                            {"id": "5", "title": "Translator", "description": "Translate text between languages."},
                            {"id": "6", "title": "Weather Forecast", "description": "Get the current weather."},
                            {"id": "7", "title": "Currency Converter", "description": "Convert between currencies."},
                            {"id": "8", "title": "AI Email Assistant", "description": "Get help writing professional emails."}
                        ]}]
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send interactive menu to {to}: {e.response.text if e.response else e}")

# --- NEW INTERACTIVE REMINDER LIST ---
def send_reminders_list(to, reminders):
    """Sends an interactive list of reminders with a delete button for each."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    if not reminders:
        send_message(to, "You have no active reminders set.")
        return

    # WhatsApp lists are limited to 10 rows per section
    reminder_rows = []
    for rem in reminders[:10]:
        reminder_rows.append({
            "id": f"delete_reminder_{rem['id']}",
            "title": rem['task'][:24], # Title is limited to 24 chars
            "description": f"Next: {rem['next_run']} ({rem['type']})"
        })

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Your Reminders ⏰"},
            "body": {"text": "Here are your active reminders. Select one to delete it."},
            "footer": {"text": "You can also type 'menu'"},
            "action": {
                "button": "Manage Reminders",
                "sections": [{"title": "Active Reminders", "rows": reminder_rows}]
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send reminders list to {to}: {e.response.text if e.response else e}")


def send_conversion_menu(to):
    """Sends an interactive LIST menu for file conversions."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "File Conversion Menu 📁"},
            "body": {"text": "Please choose a conversion type from the list below."},
            "footer": {"text": "Select one option"},
            "action": {
                "button": "Conversion Options",
                "sections": [
                    {
                        "title": "Available Conversions",
                        "rows": [
                            {"id": "conv_pdf_to_text", "title": "PDF ➡️ Text"},
                            {"id": "conv_text_to_pdf", "title": "Text ➡️ PDF"},
                            {"id": "conv_pdf_to_word", "title": "PDF ➡️ Word"},
                            {"id": "conv_text_to_word", "title": "Text ➡️ Word"}
                        ]
                    }
                ]
            }
        }
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send conversion menu to {to}: {e.response.text if e.response else e}")
