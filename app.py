from flask import Flask, request
from grok_ai import correct_grammar_with_grok
from ai import ai_reply
from reminders import schedule_reminder
from translator_module import translate_text
from weather import get_weather
import requests
import os
import time  # <- for progress simulation
from fpdf import FPDF
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from docx2pdf import convert
import fitz
import subprocess
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

VERIFY_TOKEN = "ranga123"
ACCESS_TOKEN = "EAAXPyMWrMskBO4tAwKG3gcefN1lJCffFhdVmx912RG3wfZAmllzb3k1jOXdZA2snfaJo5NoLHYGKtBIZAfH5FQWncQNgKyumjA0rahXCA3KKwJo4X4HJkBBPqguNWD24hhQ9aBz18iYaMPIXHvi777hXOZC8bsUt5qrrZAPtgSR37Qwv2R1UPvoE6qDdBDVHeqwZDZD"
PHONE_NUMBER_ID = "740671045777701"

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

        if "messages" not in entry or not entry["messages"]:
            return "No user message to process", 200

        message = entry["messages"][0]
        sender_number = message["from"]
        global user_sessions
        response_text = ""

        if message["type"] == "text":
            user_text = message["text"]["body"].strip()
            state = user_sessions.get(sender_number)

            if user_text in ["0", "menu"]:
                state = None
                user_sessions.pop(sender_number, None)

            if state == "awaiting_reminder":
                response_text = schedule_reminder(user_text, sender_number)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_grammar":
                send_progress(sender_number)  # 🔄 Progress Simulation
                response_text = correct_grammar_with_grok(user_text)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_ai":
                if user_text == "0":
                    user_sessions.pop(sender_number, None)
                    response_text = get_main_menu()
                else:
                    send_progress(sender_number)  # 🔄 Progress Simulation
                    response_text = ai_reply(user_text)

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
                send_progress(sender_number)  # 🔄 Progress Simulation
                pdf_path = convert_text_to_pdf(user_text)
                send_file_to_user(sender_number, pdf_path, "application/pdf")
                response_text = "✅ Your text was converted to PDF and sent."
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_translation":
                send_progress(sender_number)  # 🔄 Progress Simulation
                response_text = translate_text(user_text)
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_weather":
                response_text = get_weather(user_text)
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
                    response_text = "🤖 Ask me anything! (Type 0 or menu to go back)"
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
                    user_sessions[sender_number] = "awaiting_translation"
                    response_text = (
                        "🌍 Translator Selected!\n"
                        "📤 Step 1: Send your sentence starting with 'en:' or 'fr:'\n"
                        "🔄 Step 2: I will translate and send back\n"
                        "📥 Step 3: If it's voice, you'll hear it!"
                    )
                elif user_text == "6":
                    user_sessions[sender_number] = "awaiting_weather"
                    response_text = "🏙️ Please enter your location in India (e.g., Kanuru, Delhi, Mumbai):"
                else:
                    response_text = get_main_menu()

        send_message(sender_number, response_text)
        print("✅ Sent reply:", response_text)

    except Exception as e:
        print("❌ ERROR:", e)

    return "OK", 200

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

# 🔄 Progress Simulation Function
def send_progress(to, delay=1.2):
    stages = [
        "🔄 Starting... 25%",
        "⏳ Working... 50%",
        "⚙️ Almost there... 75%",
        "✅ Done! 100%"
    ]
    for stage in stages:
        send_message(to, stage)
        time.sleep(delay)

def get_main_menu():
    return (
        "👾 AI-Buddy Main Menu:\n\n"
        "🧠 1. Reminder ⏰\n"
        "📖 2. Grammar Fix ✍️\n"
        "🤖 3. Ask Me Anything 💬\n"
        "📁 4. File/Text Conversion 📄\n"
        "🌍 5. Translator 🔁\n"
        "⛅ 6. Weather Bot ☁️\n"
        "📤 Step 1: Send your sentence starting with 'en:' or 'fr:'\n"
        "🔄 Step 2: I will translate and send back\n"
        "📥 Step 3: If it's voice, you'll hear it!\n\n"
        "Reply with the number ⌨️"
    )

# NOTE: Make sure your send_file_to_user, convert_text_to_pdf, etc., are defined below

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
