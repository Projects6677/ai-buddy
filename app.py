from flask import Flask, request
from grok_ai import correct_grammar_with_grok
from ai import ai_reply
from reminders import schedule_reminder
import requests
import os
from fpdf import FPDF
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from docx2pdf import convert
import fitz  # pymupdf for pdf to text extraction
import subprocess
from pdf2image import convert_from_path
import pytesseract
from image_gen_hf import generate_image_url  # <- UPDATED IMPORT
from translator_module import translate_text  # <- NEW IMPORT

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

            if state == "awaiting_reminder":
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
                    response_text = "❓ Please send 1, 2, 3, 4 or 5 to select a conversion type."

            elif state == "awaiting_text":
                pdf_path = convert_text_to_pdf(user_text)
                send_file_to_user(sender_number, pdf_path, "application/pdf")
                response_text = "✅ Your text was converted to PDF and sent."
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_image_prompt":
                image_path = generate_image_url(user_text)
                print("🔍 Image path:", image_path)
                if image_path:
                    send_image_to_user(sender_number, image_path)
                    response_text = "✅ Generated image sent!"
                else:
                    response_text = "❌ Failed to generate image. Check prompt or try again later."
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_translation":
                response_text = translate_text(user_text)
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
                    response_text = "🖼️ Please type the description for the image you want me to generate."
                elif user_text == "6":
                    user_sessions[sender_number] = "awaiting_translation"
                    response_text = "🌐 Please enter the text you'd like translated."
                else:
                    response_text = (
                        "👋 Welcome to AI-Buddy! Choose an option:\n"
                        "1️⃣ Set a reminder\n"
                        "2️⃣ Fix grammar\n"
                        "3️⃣ Ask anything\n"
                        "4️⃣ File/Text conversion\n"
                        "5️⃣ Generate an image from text\n"
                        "6️⃣ Translator"
                    )

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

def send_file_to_user(to, file_path, mime_type):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    with open(file_path, "rb") as f:
        file_data = f.read()

    filename = os.path.basename(file_path)
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    media_upload = requests.post(
        url,
        headers=headers,
        files={"file": (filename, file_data, mime_type)},
        data={"messaging_product": "whatsapp"}
    )

    media_id = media_upload.json().get("id")
    if media_id:
        msg_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "id": media_id,
                "caption": "Here is your file."
            }
        }
        requests.post(msg_url, headers=headers, json=data)

def send_image_to_user(to, image_path):
    upload_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    files = {"file": ("generated_image.jpg", open(image_path, "rb"), "image/jpeg")}
    data = {"messaging_product": "whatsapp"}

    media_response = requests.post(upload_url, headers=headers, files=files, data=data)
    media_id = media_response.json().get("id")

    if media_id:
        message_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {
                "id": media_id,
                "caption": "Here is your generated image!"
            }
        }
        requests.post(message_url, headers=headers, json=payload)

def convert_text_to_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    lines = text.split('\n')
    for line in lines:
        pdf.multi_cell(0, 10, line)
    safe_filename = secure_filename(text[:20]) or "converted"
    path = os.path.join("/tmp", f"{safe_filename}.pdf")
    pdf.output(path)
    return path

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
