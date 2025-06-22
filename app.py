# Full updated app.py with Option 5: Image Generation via Stability AI
from flask import Flask, request
from grok_ai import correct_grammar_with_grok
from ai import ai_reply
from reminders import schedule_reminder
import requests
import os
import uuid
from fpdf import FPDF
from werkzeug.utils import secure_filename

from imagegen import generate_image

app = Flask(__name__)

VERIFY_TOKEN = "ranga123"
ACCESS_TOKEN = "740671045777701"
PHONE_NUMBER_ID = "EAAXPyMWrMskBO37ND9oRE1kNdlIQ8ZA2ZAr0RDdUZCYLAuoHpkkokNUfPR6k1ON6AyGu3RRTtHl2ESm6NKeXHMEPN9ujio5aqF2cGftQUFrYwG36zf9Y4xrxLBRp2mURKpUeoHMBZAZB5AZBweYQ0lHaCstALIZB3q05iRrgsZCC5GfTyPZAb4ZCrzgRm5OD2tJDr0gAZDZD"

user_sessions = {}

@app.route('/')
def home():
    return "WhatsApp AI Assistant with Conversions is Live!"

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("\n🚀 Received message:", data)

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" not in entry:
            return "No message to handle", 200

        message = entry["messages"][0]
        sender_number = message["from"]

        global user_sessions
        response_text = ""

        if message["type"] == "text":
            user_text = message["text"]["body"].strip()
            state = user_sessions.get(sender_number)

            if state == "awaiting_image_prompt":
                img_path = generate_image(user_text)
                send_file_to_user(sender_number, img_path, "image/png")
                response_text = "🖼️ Your AI-generated image is ready!"
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_reminder":
                response_text = schedule_reminder(user_text, sender_number)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_grammar":
                response_text = correct_grammar_with_grok(user_text)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_ai":
                response_text = ai_reply(user_text)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_conversion_choice":
                if user_text == "1":
                    user_sessions[sender_number] = "awaiting_pdf"
                    response_text = "📥 Please upload a PDF file to convert to text."
                elif user_text == "2":
                    user_sessions[sender_number] = "awaiting_docx"
                    response_text = "📥 Please upload a Word (.docx) file to convert to PDF."
                elif user_text == "3":
                    user_sessions[sender_number] = "awaiting_text"
                    response_text = "📝 Please send the text you want to convert into a PDF."
                elif user_text == "4":
                    user_sessions[sender_number] = "awaiting_pdf_to_docx"
                    response_text = "📥 Please upload the PDF to convert into Word."
                else:
                    response_text = "❓ Please send 1, 2, 3 or 4 to select a conversion type."

            elif state == "awaiting_text":
                pdf_path = convert_text_to_pdf(user_text)
                send_file_to_user(sender_number, pdf_path, "application/pdf")
                response_text = "✅ Your text was converted to PDF and sent."
                user_sessions.pop(sender_number, None)

            else:
                if user_text == "1":
                    user_sessions[sender_number] = "awaiting_reminder"
                    response_text = "🕒 Please type your reminder like:\nRemind me to [task] at [time]"
                elif user_text == "2":
                    user_sessions[sender_number] = "awaiting_grammar"
                    response_text = "✍️ Please type the sentence you want me to correct."
                elif user_text == "3":
                    user_sessions[sender_number] = "awaiting_ai"
                    response_text = "🤖 Ask me anything!"
                elif user_text == "4":
                    user_sessions[sender_number] = "awaiting_conversion_choice"
                    response_text = (
                        "📂 Choose conversion type:\n"
                        "1️⃣ PDF to Text\n"
                        "2️⃣ Word to PDF\n"
                        "3️⃣ Text to PDF\n"
                        "4️⃣ PDF to Word"
                    )
                elif user_text == "5":
                    user_sessions[sender_number] = "awaiting_image_prompt"
                    response_text = "🎨 What do you want me to draw? Describe the image."
                else:
                    response_text = (
                        "👋 Welcome to AI-Buddy! Choose an option:\n"
                        "1️⃣ Set a reminder\n"
                        "2️⃣ Fix grammar\n"
                        "3️⃣ Ask anything\n"
                        "4️⃣ File/Text conversion\n"
                        "5️⃣ AI Image Generator"
                    )

        send_message(sender_number, response_text)
    except Exception as e:
        print("❌ ERROR:", e)

    return "OK", 200

# File conversion and other helper functions remain same below
# ... (unchanged code omitted for brevity)
