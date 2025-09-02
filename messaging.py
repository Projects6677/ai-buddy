# messaging.py
import requests
import os
import time

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_VERSION = "v19.0"

def send_message(to, message):
    """Sends a standard text message."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
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
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
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
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    welcome_text = f"👋 Welcome back, *{name}*!\n\nHow can I assist you today? You can also type commands like `.reminders` to see your reminders."

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
                            {"id": "2", "title": "Fix Grammar", "description": "Correct spelling and grammar."},
                            {"id": "3", "title": "Ask AI Anything", "description": "Chat with the AI assistant."},
                            {"id": "4", "title": "File/Text Conversion", "description": "Convert between PDF and Word."},
                            {"id": "5", "title": "Weather Forecast", "description": "Get the current weather."},
                            {"id": "6", "title": "Currency Converter", "description": "Convert between currencies."},
                            {"id": "7", "title": "AI Email Assistant", "description": "Get help writing professional emails."},
                            {"id": "8", "title": "Google Drive", "description": "Manage and analyze files in your Drive."}
                        ]}]
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send interactive menu to {to}: {e.response.text if e.response else e}")

def send_reminders_list(to, reminders):
    """Sends an interactive list of reminders with a delete button for each."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    if not reminders:
        send_message(to, "You have no active reminders set.")
        return

    reminder_rows = []
    for rem in reminders[:10]:
        reminder_rows.append({
            "id": f"delete_reminder_{rem['id']}",
            "title": rem['task'][:24],
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

def send_delete_confirmation(to, job_id, task_name):
    """Sends a yes/no confirmation message for deleting a reminder."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": f"Are you sure you want to delete the reminder for:\n\n*{task_name}*?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"confirm_delete_{job_id}",
                            "title": "Yes, Delete"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cancel_delete",
                            "title": "No, Cancel"
                        }
                    }
                ]
            }
        }
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send delete confirmation to {to}: {e.response.text if e.response else e}")

def send_meeting_proposal(to, proposed_time, session_id):
    """Sends a yes/no confirmation for a proposed meeting time."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    formatted_time = proposed_time.strftime('%A, %b %d at %I:%M %p')
    
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": f"🗓️ I found an available slot for everyone on:\n\n*{formatted_time}*\n\nWould you like me to schedule it?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"confirm_meeting_{session_id}",
                            "title": "Yes, Schedule It"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cancel_meeting",
                            "title": "No, Cancel"
                        }
                    }
                ]
            }
        }
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send meeting proposal to {to}: {e.response.text if e.response else e}")


def send_conversion_menu(to):
    """Sends an interactive LIST menu for file conversions."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
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

def send_google_drive_menu(to):
    """Sends the interactive Google Drive menu."""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
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
            "header": {"type": "text", "text": "Google Drive Options 📁"},
            "body": {"text": "How would you like to use Google Drive?"},
            "footer": {"text": "Please select an option"},
            "action": {
                "button": "Drive Features",
                "sections": [
                    {
                        "title": "Available Actions",
                        "rows": [
                            {"id": "drive_upload_file", "title": "Upload a File", "description": "Save a document from WhatsApp to Drive."},
                            {"id": "drive_search_file", "title": "Search for a File", "description": "Find a file in your Drive by name."},
                            {"id": "drive_analyze_file", "title": "Analyze a File", "description": "Summarize or ask questions about a file."},
                        ]
                    }
                ]
            }
        }
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Google Drive menu to {to}: {e.response.text if e.response else e}")
