from flask import Flask, request
import requests
import os
import time
from datetime import datetime
import json
from fpdf import FPDF
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import fitz  # PyMuPDF
import pytesseract
from docx import Document

# --- Imports for the Reminder feature ---
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil import parser as date_parser
import pytz

# --- Mock functions for other modules ---
def correct_grammar_with_grok(text): return f"Grammar checked for: `{text}`"
def ai_reply(text): return f"🤖 Here's what I think about `{text}`..."
def translate_text(text): return f"🌍 Translated text: `{text}`"
def get_weather(city): return f"The weather in {city} is currently sunny. ☀️"
# --- End of mock functions ---


app = Flask(__name__)

# === CONFIG ===
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ranga123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

USER_DATA_FILE = "user_data.json"
user_sessions = {}

# --- Initialize the Scheduler ---
# Using the timezone from your code
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
scheduler.start()


if not os.path.exists("uploads"):
    os.makedirs("uploads")

# === JSON MEMORY ===
def load_user_data():
    if not os.path.exists(USER_DATA_FILE): return {}
    try:
        with open(USER_DATA_FILE, "r") as f: return json.load(f)
    except json.JSONDecodeError: return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f: json.dump(data, f, indent=4)

# === ROUTES ===
@app.route('/')
def home():
    return "WhatsApp AI Assistant is Live!"

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN: return challenge, 200
    return "Verification failed", 403

def download_media_from_whatsapp(media_id):
    try:
        url = f"https://graph.facebook.com/v19.0/{media_id}/"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        media_info = response.json()
        media_url = media_info['url']
        download_response = requests.get(media_url, headers=headers)
        download_response.raise_for_status()
        temp_filename = secure_filename(media_id)
        file_path = os.path.join("uploads", temp_filename)
        with open(file_path, "wb") as f: f.write(download_response.content)
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading media: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("\n🚀 Received message:", json.dumps(data, indent=2))
    try:
        entry = data.get("entry", [])[0].get("changes", [])[0].get("value", {})
        if "messages" not in entry or not entry["messages"]: return "OK", 200
        message = entry["messages"][0]
        sender_number = message["from"]
        state = user_sessions.get(sender_number)
        msg_type = message.get("type")
        if msg_type == "document":
            handle_document_message(message, sender_number, state)
        elif msg_type == "interactive":
            handle_interactive_reply(message, sender_number)
        elif msg_type == "text":
            handle_text_message(message, sender_number, state)
        else:
            send_message(sender_number, "🤔 Sorry, I can only process text and documents at the moment.")
    except Exception as e:
        print(f"❌ Unhandled Error: {e}")
    return "OK", 200

# === MESSAGE HANDLERS ===
def handle_document_message(message, sender_number, state):
    media_id = message["document"]["id"]
    send_message(sender_number, f"Got your file! 📄 Processing...")
    downloaded_path = download_media_from_whatsapp(media_id)
    if not downloaded_path:
        send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
        return
    if state == "awaiting_pdf_to_text":
        extracted_text = extract_text_from_pdf_file(downloaded_path)
        response = extracted_text if extracted_text else "Could not find any readable text in the PDF."
        send_message(sender_number, response)
    elif state == "awaiting_pdf_to_docx":
        output_docx_path = downloaded_path + ".docx"
        cv = Converter(downloaded_path)
        cv.convert(output_docx_path, start=0, end=None)
        cv.close()
        send_file_to_user(sender_number, output_docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
        if os.path.exists(output_docx_path): os.remove(output_docx_path)
    else:
        send_message(sender_number, "I received a file, but I wasn't expecting one. Try the menu first!")
    if os.path.exists(downloaded_path): os.remove(downloaded_path)
    user_sessions.pop(sender_number, None)

def handle_interactive_reply(message, sender_number):
    interactive_type = message["interactive"]["type"]
    response_text = ""
    if interactive_type == "list_reply":
        reply_id = message["interactive"]["list_reply"]["id"]
        if reply_id == "menu_reminder":
            user_sessions[sender_number] = "awaiting_reminder"
            response_text = "🕒 What should I remind you about?\n\n_Example: Remind me to call Mom at 7pm_"
        elif reply_id == "menu_grammar":
            user_sessions[sender_number] = "awaiting_grammar"
            response_text = "✍️ Send me the sentence or paragraph you want to correct."
        elif reply_id == "menu_ai":
            user_sessions[sender_number] = "awaiting_ai"
            response_text = "🤖 You can now chat with me! Ask me anything.\n\n_Type `menu` to exit this mode._"
        elif reply_id == "menu_conversion":
            send_conversion_menu(sender_number)
        elif reply_id == "menu_translator":
            user_sessions[sender_number] = "awaiting_translation"
            response_text = "🌍 Translator active!\n\n_Example: `en:Hello world`_"
        elif reply_id == "menu_weather":
            user_sessions[sender_number] = "awaiting_weather"
            response_text = "🏙️ Which city's weather would you like to know?"
    elif interactive_type == "button_reply":
        reply_id = message["interactive"]["button_reply"]["id"]
        if reply_id == "conv_pdf_to_text":
            user_sessions[sender_number] = "awaiting_pdf_to_text"
            response_text = "📥 Please upload the PDF you want to convert to text."
        elif reply_id == "conv_text_to_pdf":
            user_sessions[sender_number] = "awaiting_text_to_pdf"
            response_text = "📝 Please send the text you want to convert into a PDF."
        elif reply_id == "conv_pdf_to_docx":
            user_sessions[sender_number] = "awaiting_pdf_to_docx"
            response_text = "📥 Please upload the PDF to convert into Word."
        elif reply_id == "conv_text_to_word":
            user_sessions[sender_number] = "awaiting_text_to_word"
            response_text = "📝 Please send the text you want to convert into a Word document."
    if response_text:
        send_message(sender_number, response_text)

def handle_text_message(message, sender_number, state):
    user_text = message["text"]["body"].strip()
    user_data = load_user_data()
    response_text = ""
    
    if user_text.lower() in ["hi", "hello", "hey", "start", "menu", "help", "options", "0"]:
        user_sessions.pop(sender_number, None)
        name = user_data.get(sender_number, {}).get("name")
        if not name:
            response_text = "👋 Hi there! To personalize your experience, what should I call you?"
            user_sessions[sender_number] = "awaiting_name"
        else:
            send_interactive_menu(sender_number, name)
    
    elif state == "awaiting_name":
        name = user_text.split()[0].title()
        user_data[sender_number] = {"name": name}
        save_user_data(user_data)
        user_sessions.pop(sender_number, None)
        send_message(sender_number, f"✅ Got it! I’ll remember you as *{name}*.")
        time.sleep(1)
        send_interactive_menu(sender_number, name)

    elif state == "awaiting_reminder":
        response_text = schedule_reminder(user_text, sender_number)
        user_sessions.pop(sender_number, None)

    elif state == "awaiting_grammar":
        response_text = correct_grammar_with_grok(user_text)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_ai":
        response_text = ai_reply(user_text)
    elif state == "awaiting_translation":
        response_text = translate_text(user_text)
    elif state == "awaiting_weather":
        response_text = get_weather(user_text)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_text_to_pdf":
        pdf_path = convert_text_to_pdf(user_text)
        send_file_to_user(sender_number, pdf_path, "application/pdf", "📄 Here is your converted PDF file.")
        if os.path.exists(pdf_path): os.remove(pdf_path)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_text_to_word":
        docx_path = convert_text_to_word(user_text)
        send_file_to_user(sender_number, docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
        if os.path.exists(docx_path): os.remove(docx_path)
        user_sessions.pop(sender_number, None)
    else:
        response_text = "🤔 I'm not sure what you mean. Please choose an option from the `menu`."

    if response_text:
        send_message(sender_number, response_text)

# === UI, HELPERS, & REMINDER LOGIC ===
def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message, "preview_url": False}}
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")

# --- NEW: Fully functional reminder logic inspired by your code ---
def schedule_reminder(user_text, sender_number):
    try:
        # Split the message to find the task and the time
        parts = user_text.lower().split("remind me to")[1].strip().split(" at ")
        task = parts[0].strip()
        time_string = parts[1].strip()

        # Use dateutil.parser to figure out the datetime
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        run_time = date_parser.parse(time_string, default=now)

        # If the parsed time is in the past, assume it's for the next day
        if run_time < now:
            run_time = run_time.replace(day=run_time.day + 1)

        # The message to be sent when the reminder is due
        reminder_message = f"⏰ *Reminder:* {task.capitalize()}"

        # Add the job to the scheduler
        scheduler.add_job(
            func=send_message,
            trigger='date',
            run_date=run_time,
            args=[sender_number, reminder_message],
            id=f"{sender_number}-{task}-{run_time.timestamp()}", # A unique ID for the job
            replace_existing=True
        )

        return f"✅ Reminder set for *{task}* at *{run_time.strftime('%I:%M %p')}*."

    except Exception as e:
        print(f"❌ Reminder error: {e}")
        return "❌ Could not set reminder. Please use the format: _Remind me to [task] at [time]_"

def send_interactive_menu(to, name):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": f"👋 Welcome, {name}!"},
            "body": {"text": "What can I help you with today? Choose an option below."},
            "footer": {"text": "AI Buddy"},
            "action": { "button": "View Options", "sections": [
                    { "title": "Productivity", "rows": [
                        {"id": "menu_reminder", "title": "⏰ Set a Reminder"},
                        {"id": "menu_grammar", "title": "✍️ Fix Grammar"},
                        {"id": "menu_conversion", "title": "📄 File Conversion"}]},
                    { "title": "Knowledge & Fun", "rows": [
                        {"id": "menu_ai", "title": "💬 Ask AI Anything"},
                        {"id": "menu_translator", "title": "🌍 Translator"},
                        {"id": "menu_weather", "title": "⛅ Get Weather"}]}
                ]}}}
    requests.post(url, headers=headers, json=payload)

def send_conversion_menu(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "📁 *File/Text Conversion Menu*\n\nWhich type of conversion would you like to perform?"},
            "action": { "buttons": [
                    {"type": "reply", "reply": {"id": "conv_pdf_to_text", "title": "PDF ➡️ Text"}},
                    {"type": "reply", "reply": {"id": "conv_text_to_pdf", "title": "Text ➡️ PDF"}},
                    {"type": "reply", "reply": {"id": "conv_pdf_to_docx", "title": "PDF ➡️ Word"}},
                ]}}}
    requests.post(url, headers=headers, json=payload)
    time.sleep(1)
    send_message(to, "For `Text ➡️ Word`, please send me the text you want to convert.")
    user_sessions[to] = "awaiting_text_to_word"

def convert_text_to_pdf(text):
    pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    text_encoded = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, text_encoded)
    filename = secure_filename(f"converted_{int(time.time())}.pdf")
    file_path = os.path.join("uploads", filename)
    pdf.output(file_path); return file_path
    
def convert_text_to_word(text):
    document = Document(); document.add_paragraph(text)
    filename = secure_filename(f"converted_{int(time.time())}.docx")
    file_path = os.path.join("uploads", filename)
    document.save(file_path); return file_path

def extract_text_from_pdf_file(file_path):
    try:
        with fitz.open(file_path) as doc: text = "".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting PDF text: {e}"); return ""

def send_file_to_user(to, file_path, mime_type, caption="Here is your file."):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    with open(file_path, "rb") as f:
        files = {'file': (os.path.basename(file_path), f, mime_type)}
        data = {"messaging_product": "whatsapp"}
        upload_response = requests.post(url, headers=headers, files=files, data=data)
    if upload_response.status_code != 200:
        print(f"Error uploading file: {upload_response.text}"); return
    media_id = upload_response.json().get("id")
    if not media_id: return
    message_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "document", "document": {"id": media_id, "caption": caption}}
    requests.post(message_url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}, json=payload)

# === RUN APP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
