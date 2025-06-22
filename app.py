# Full app.py with Option 4 + File Sending Back via WhatsApp
from flask import Flask, request
from grok_ai import correct_grammar_with_grok
from ai import ai_reply
from reminders import schedule_reminder
import requests
import os
import uuid
from fpdf import FPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)

VERIFY_TOKEN = "ranga123"
ACCESS_TOKEN = "EAAXPyMWrMskBOZCicTVIgGHAUZC7szcMigr9lICZBiZChS5NM4XlrUtVkaQsiBSHhKEaiFBOXcOuhqMFZC9ZA0F8gkmWvquZA8Rv6dbbdduOgbT7ZBOfYrV2uLwbxODeW1r4ZCLZATys7o6aw7h0ORPqRnai8TmVDm9msdiDyvHzz2D2akORUL0m0NXrd27BexTbAH209gPJWiJ3FLEek8aBZB5qDgHZCocr3QGD3rzka7xw"
PHONE_NUMBER_ID = "698497970011796"

user_sessions = {}  # Stores what user is doing (e.g., awaiting text, awaiting file)

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

        # Handle media (for file uploads)
        if message["type"] == "document":
            media_id = message["document"]["id"]
            filename = message["document"]["filename"]
            mime_type = message["document"]["mime_type"]
            print("📎 File received:", filename, mime_type)

            file_path = download_media(media_id, filename)
            task = user_sessions.get(sender_number)

            if task == "awaiting_pdf":
                converted = convert_pdf_to_text(file_path)
                response_text = f"✅ Extracted text:\n{converted[:1000]}..."
            elif task == "awaiting_docx":
                pdf_path = convert_docx_to_pdf(file_path)
                send_file_to_user(sender_number, pdf_path, "application/pdf")
                response_text = "✅ Word file converted to PDF."
            else:
                response_text = "❗I got your file but didn't understand what to do. Please choose option 4 again."
            user_sessions.pop(sender_number, None)
        
        elif message["type"] == "text":
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
                else:
                    response_text = "❓ Please send 1, 2 or 3 to select a conversion type."

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
                        "3️⃣ Text to PDF"
                    )
                else:
                    response_text = (
                        "👋 Welcome to AI-Buddy! Choose an option:\n"
                        "1️⃣ Set a reminder\n"
                        "2️⃣ Fix grammar\n"
                        "3️⃣ Ask anything\n"
                        "4️⃣ File/Text conversion"
                    )

        send_message(sender_number, response_text)
    except Exception as e:
        print("❌ ERROR:", e)

    return "OK", 200


def download_media(media_id, filename):
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    media_info = requests.get(url, headers=headers).json()
    file_url = media_info['url']

    file_data = requests.get(file_url, headers=headers)
    path = os.path.join("/tmp", secure_filename(filename))
    with open(path, "wb") as f:
        f.write(file_data.content)
    print("✅ File downloaded to:", path)
    return path


def convert_text_to_pdf(text):
    filename = f"/tmp/{uuid.uuid4().hex}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(filename)
    print("✅ Text converted to PDF:", filename)
    return filename


def convert_pdf_to_text(pdf_path):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text() for page in doc])
        return text
    except:
        return "⚠️ Failed to convert PDF."


def convert_docx_to_pdf(docx_path):
    pdf_path = f"/tmp/{uuid.uuid4().hex}.pdf"
    from docx import Document
    document = Document(docx_path)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for para in document.paragraphs:
        pdf.multi_cell(0, 10, para.text)
    pdf.output(pdf_path)
    print("✅ DOCX converted to PDF:", pdf_path)
    return pdf_path


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
    print("📤 Sent message:", response.status_code, response.text)


def send_file_to_user(to, file_path, mime_type):
    # Upload media to WhatsApp first
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), mime_type)}
    payload = {'messaging_product': 'whatsapp'}
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    upload_resp = requests.post(url, headers=headers, files=files, data=payload)
    print("📤 Upload response:", upload_resp.status_code, upload_resp.text)
    media_id = upload_resp.json().get("id")

    if media_id:
        send_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        send_data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "id": media_id,
                "caption": "Here is your converted file"
            }
        }
        send_resp = requests.post(send_url, headers=headers, json=send_data)
        print("📄 Sent document:", send_resp.status_code, send_resp.text)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
