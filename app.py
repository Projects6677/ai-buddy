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
import time

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

def download_media(media_url, filename):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(media_url, headers=headers)
    if response.status_code == 200:
        path = os.path.join("/tmp", filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return path
    else:
        print("❌ Failed to download media:", response.status_code)
        return None

def ocr_pdf_to_text(pdf_path):
    try:
        pages = convert_from_path(pdf_path)
        text = ""
        for i, page in enumerate(pages):
            page_text = pytesseract.image_to_string(page)
            print(f"OCR Page {i+1} text length: {len(page_text)}")
            text += page_text + "\n"
        return text
    except Exception as e:
        print("❌ OCR PDF to text conversion error:", e)
        return None

def convert_pdf_to_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for i, page in enumerate(doc):
            page_text = page.get_text()
            print(f"Page {i+1} text length: {len(page_text)}")  # Debug output
            text += page_text
        doc.close()
        if not text.strip():
            print("⚠️ No text extracted — trying OCR fallback...")
            text = ocr_pdf_to_text(pdf_path)
        return text
    except Exception as e:
        print("❌ PDF to text conversion error:", e)
        return None

def convert_pdf_to_docx(pdf_path):
    docx_path = pdf_path.replace(".pdf", ".docx")
    try:
        if not os.path.exists(pdf_path):
            print("❌ PDF file does not exist:", pdf_path)
            return None
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        return docx_path
    except Exception as e:
        print("❌ PDF to DOCX conversion error:", e)
        return None

def convert_docx_to_pdf(docx_path):
    pdf_path = docx_path.replace(".docx", ".pdf")
    try:
        if os.name == 'posix' and not os.environ.get("MS_WORD_INSTALLED"):
            # Assume Linux without MS Word, use LibreOffice CLI fallback
            cmd = ['libreoffice', '--headless', '--convert-to', 'pdf', docx_path, '--outdir', os.path.dirname(docx_path)]
            subprocess.run(cmd, check=True)
            if os.path.exists(pdf_path):
                return pdf_path
            else:
                print("❌ LibreOffice conversion failed: output PDF not found.")
                return None
        else:
            # Use docx2pdf normally on Windows/macOS with MS Word installed
            convert(docx_path, pdf_path)
            if os.path.exists(pdf_path):
                return pdf_path
            else:
                print("❌ PDF output not found after conversion.")
                return None
    except Exception as e:
        print("❌ DOCX to PDF conversion error:", e)
        return None

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

        state = user_sessions.get(sender_number)

        # Handle document uploads for conversions
        if message["type"] == "document":
            media_id = message["document"]["id"]
            filename = message["document"].get("filename", f"file_{media_id}")

            # Get media URL from WhatsApp
            media_url_response = requests.get(
                f"https://graph.facebook.com/v19.0/{media_id}",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )
            media_url_response.raise_for_status()
            media_url = media_url_response.json().get("url")

            if not media_url:
                send_message(sender_number, "❌ Could not get media URL.")
                return "OK", 200

            # Download the file locally
            file_path = download_media(media_url, secure_filename(filename))
            if not file_path:
                send_message(sender_number, "❌ Failed to download the file.")
                return "OK", 200

            # Process according to user session state
            if state == "awaiting_pdf":
                # PDF to Text
                extracted_text = convert_pdf_to_text(file_path)
                if extracted_text:
                    send_message(sender_number, f"📄 Extracted text:\n{extracted_text[:1000]}")
                else:
                    send_message(sender_number, "❌ Failed to extract text from PDF.")
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_pdf_to_docx":
                # PDF to DOCX
                docx_path = convert_pdf_to_docx(file_path)
                if docx_path:
                    send_file_to_user(sender_number, docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                else:
                    send_message(sender_number, "❌ Failed to convert PDF to Word.")
                user_sessions.pop(sender_number, None)

            elif state == "awaiting_docx":
                # DOCX to PDF
                pdf_path = convert_docx_to_pdf(file_path)
                if pdf_path:
                    send_file_to_user(sender_number, pdf_path, "application/pdf")
                else:
                    send_message(sender_number, "❌ Failed to convert Word to PDF.")
                user_sessions.pop(sender_number, None)

            else:
                send_message(sender_number, "❌ Unexpected file upload. Please select an option first.")

            return "OK", 200

        # Text message handling (unchanged)
        if message["type"] == "text":
            user_text = message["text"]["body"].strip()

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
                else:
                    response_text = (
                        "👋 Welcome to AI-Buddy! Choose an option:\n"
                        "1️⃣ Set a reminder\n"
                        "2️⃣ Fix grammar\n"
                        "3️⃣ Ask anything\n"
                        "4️⃣ File/Text conversion"
                    )

            send_message(sender_number, response_text)
            print("✅ Sent reply:", response_text)

    except Exception as e:
        print("❌ ERROR:", e)

    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
