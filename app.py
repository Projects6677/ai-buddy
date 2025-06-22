from flask import Flask, request
from grok_ai import correct_grammar_with_grok
from ai import ai_reply
from reminders import schedule_reminder
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "ranga123"
ACCESS_TOKEN = "EAAJ0jnn2gyMBO0wSo7dZCIVnceSx0AapQ7IWvL1MOggG6jEXVR4pi7Gqtjbgvbi2AgWWvNb7fPs9TQCRgZA32a13OrARh0ZBZBNKrcQkv7ZBZAHHtU7ddINVue9M6WJHjbg0zZCj9M6lDPMvRrfyu6ZAsuzZByIioeGfvxRzMQ9BHlCT8c2B5gvh6cjIs4Go5vZAilbH5blsGeUZAlgWVdnC9dvsUNgBuJ7ODvrBMXzXZBGtnZALf28UZD"
PHONE_NUMBER_ID = "698497970011796"

# Store temporary user sessions
user_sessions = {}

@app.route('/')
def home():
    return "WhatsApp AI Assistant is Live!"

# Webhook verification for Meta
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403

# Webhook to handle incoming messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("🚀 Received message:", data)  # Debug log to confirm message reception

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        message = entry["messages"][0]
        user_text = message["text"]["body"].strip()
        sender_number = message["from"]

        global user_sessions
        response_text = ""

        # Check if user is in an active session
        if sender_number in user_sessions:
            state = user_sessions[sender_number]

            if state == "awaiting_reminder":
                response_text = schedule_reminder(user_text, sender_number)
                del user_sessions[sender_number]

            elif state == "awaiting_grammar":
                response_text = correct_grammar_with_grok(user_text)
                del user_sessions[sender_number]

            elif state == "awaiting_ai":
                response_text = ai_reply(user_text)
                del user_sessions[sender_number]

            else:
                response_text = "⚠️ Unexpected state. Resetting session."
                del user_sessions[sender_number]

        else:
            # Show menu or begin new session
            if user_text == "1":
                user_sessions[sender_number] = "awaiting_reminder"
                response_text = "🕒 Please type your reminder like:\nRemind me to [task] at [time]"

            elif user_text == "2":
                user_sessions[sender_number] = "awaiting_grammar"
                response_text = "✍️ Please type the sentence you want me to correct."

            elif user_text == "3":
                user_sessions[sender_number] = "awaiting_ai"
                response_text = "🤖 Ask me anything!"

            else:
                response_text = (
                    "👋 Welcome to AI-Buddy! Choose an option:\n"
                    "1️⃣ Set a reminder\n"
                    "2️⃣ Fix grammar\n"
                    "3️⃣ Ask anything\n\n"
                    "Reply with 1, 2, or 3 to begin."
                )

        send_message(sender_number, response_text)

    except Exception as e:
        print("❌ ERROR:", e)

    return "OK", 200

# Function to send message back to WhatsApp user
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

    response = requests.post(url, headers=headers, json=data)
    print("📤 Sent message response:", response.status_code, response.text)  # Log outgoing message

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
