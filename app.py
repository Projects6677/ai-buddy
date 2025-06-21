from flask import Flask, request
from grammar import correct_grammar
from ai import ai_reply
from reminders import schedule_reminder
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "ranga123"
ACCESS_TOKEN = "EAAJ0jnn2gyMBO7qaQPmalfFVqusr5zoZCuSwPy148FvvWzQA1CGhBgiPVJS4SHhNdAzAo9UHqHaQhHZCMPIB9BRzdIETq2grq2HwVBzrS3YbmRfYu3RUG3oQJ4ZCviyFhCK7q2IVhntst6ZAG6BGjGhsLZAVQLHXvSqxeWcNw9QwE0ZAgBnPF7tRtmqgj6BcfPxZA99LIrVz0gdwV7DJ4aXTPwLBzOSHr64v2CUPFmok8ZB3EQZDZD"  # Paste from Meta
PHONE_NUMBER_ID = "698497970011796"

@app.route('/')
def home():
    return "WhatsApp AI Assistant is Live!"

# Webhook verification
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
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        message = entry["messages"][0]
        user_text = message["text"]["body"]
        sender_number = message["from"]

        response_text = ""

        # 1. Check for reminder keyword
        if "remind me to" in user_text.lower():
            response_text = schedule_reminder(user_text, sender_number)

        # 2. Check for grammar check
        elif "check grammar:" in user_text.lower():
            sentence = user_text.split(":", 1)[1]
            response_text = correct_grammar(sentence.strip())

        # 3. AI mode
        elif "ai:" in user_text.lower():
            prompt = user_text.split(":", 1)[1]
            response_text = ai_reply(prompt.strip())

        # 4. Default fallback
        else:
            response_text = "Hey! I can:\n1️⃣ Remind you\n2️⃣ Fix grammar (use 'Check grammar:')\n3️⃣ Answer anything (use 'AI:')"

        # Send the response back
        send_message(sender_number, response_text)
    except Exception as e:
        print("Error:", e)

    return "OK", 200

# Function to send message back to user
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

