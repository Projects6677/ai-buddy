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
from docx import Document # Import for creating Word docs

# --- Mock functions for modules you might have ---
def correct_grammar_with_grok(text): return f"Grammar checked for: {text}"
def ai_reply(text): return f"AI reply for: {text}"
def schedule_reminder(text, sender): return "Reminder has been set."
def translate_text(text): return f"Translated text for: {text}"
def get_weather(city): return f"The weather in {city} is sunny."
# --- End of mock functions ---


app = Flask(__name__)

# === CONFIG ===
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ranga123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

USER_DATA_FILE = "user_data.json"
user_sessions = {}

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# === JSON MEMORY ===
def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# === ROUTES ===
@app.route('/')
def home():
    return "WhatsApp AI Assistant is Live!"

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
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
        with open(file_path, "wb") as f:
            f.write(download_response.content)
        
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
        if "messages" not in entry or not entry["messages"]:
            return "OK", 200

        message = entry["messages"][0]
        sender_number = message["from"]
        state = user_sessions.get(sender_number)

        if message.get("type") == "document":
            media_id = message["document"]["id"]
            downloaded_path = None
            
            if state == "awaiting_pdf_to_text":
                send_message(sender_number, "✅ Received PDF. Extracting text...")
                downloaded_path = download_media_from_whatsapp(media_id)
                if downloaded_path:
                    extracted_text = extract_text_from_pdf_file(downloaded_path)
                    response = extracted_text if extracted_text else "Could not find any readable text in the PDF."
                    send_message(sender_number, response)
                    os.remove(downloaded_path)
                    user_sessions.pop(sender_number, None)
                else:
                    send_message(sender_number, "❌ Sorry, I couldn't process your file.")
                return "OK", 200
            
            elif state == "awaiting_pdf_to_docx":
                send_message(sender_number, "✅ Received PDF. Converting to Word...")
                downloaded_path = download_media_from_whatsapp(media_id)
                if downloaded_path:
                    output_docx_path = downloaded_path + ".docx"
                    cv = Converter(downloaded_path)
                    cv.convert(output_docx_path, start=0, end=None)
                    cv.close()
                    send_file_to_user(sender_number, output_docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
                    os.remove(downloaded_path)
                    os.remove(output_docx_path)
                    user_sessions.pop(sender_number, None)
                else:
                    send_message(sender_number, "❌ Sorry, I couldn't process your file.")
                return "OK", 200
            
            else:
                send_message(sender_number, "I received a file, but I wasn't expecting one. Please select an option from the menu first.")
                return "OK", 200
        
        user_text = ""
        if message.get("type") == "text":
            user_text = message["text"]["body"].strip()
        else:
            send_message(sender_number, "I can only process text and documents at the moment.")
            return "OK", 200

        user_data = load_user_data()
        response_text = ""

        if user_text.lower() in ["hi", "hello", "hey", "start"]:
            if sender_number not in user_data:
                send_message(sender_number, "👋 Hi there! What should I call you?")
                user_sessions[sender_number] = "awaiting_name"
            else:
                send_startup_effect(sender_number)
                send_welcome_message(sender_number, user_data[sender_number]["name"])
            return "OK", 200

        if state == "awaiting_name":
            name = user_text.split()[0].capitalize()
            user_data[sender_number] = {"name": name}
            save_user_data(user_data)
            user_sessions.pop(sender_number, None)
            send_message(sender_number, f"✅ Got it! I’ll remember your name is *{name}* 😊")
            send_welcome_message(sender_number, name)
            return "OK", 200

        if user_text.lower() in ["menu", "help", "options", "0"]:
            user_sessions.pop(sender_number, None)
            send_message(sender_number, get_main_menu(sender_number))
            return "OK", 200

        if state == "awaiting_reminder":
            response_text = schedule_reminder(user_text, sender_number)
            user_sessions.pop(sender_number, None)

        elif state == "awaiting_grammar":
            send_progress(sender_number)
            response_text = correct_grammar_with_grok(user_text)
            user_sessions.pop(sender_number, None)

        elif state == "awaiting_ai":
            if user_text == "0":
                user_sessions.pop(sender_number, None)
                response_text = get_main_menu(sender_number)
            else:
                send_progress(sender_number)
                response_text = ai_reply(user_text)

        elif state == "awaiting_conversion_choice":
            if user_text == "1":
                user_sessions[sender_number] = "awaiting_pdf_to_text"
                response_text = "📥 Please upload the PDF you want to convert to text."
            elif user_text == "2":
                user_sessions[sender_number] = "awaiting_text_to_pdf"
                response_text = "📝 Please send the text you want to convert into a PDF."
            elif user_text == "3":
                user_sessions[sender_number] = "awaiting_pdf_to_docx"
                response_text = "📥 Please upload the PDF to convert into Word."
            elif user_text == "4":
                user_sessions[sender_number] = "awaiting_text_to_word"
                response_text = "📝 Please send the text you want to convert into a Word document."
            else:
                response_text = "❓ Please send 1, 2, 3 or 4 to choose a conversion type."

        elif state == "awaiting_text_to_pdf":
            send_progress(sender_number)
            pdf_path = convert_text_to_pdf(user_text)
            send_file_to_user(sender_number, pdf_path, "application/pdf", "📄 Here is your converted PDF file.")
            os.remove(pdf_path)
            user_sessions.pop(sender_number, None)
        
        elif state == "awaiting_text_to_word":
            send_progress(sender_number)
            docx_path = convert_text_to_word(user_text)
            send_file_to_user(sender_number, docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
            os.remove(docx_path)
            user_sessions.pop(sender_number, None)

        elif state == "awaiting_translation":
            send_progress(sender_number)
            response_text = translate_text(user_text)
            user_sessions.pop(sender_number, None)

        elif state == "awaiting_weather":
            response_text = get_weather(user_text)
            user_sessions.pop(sender_number, None)

        else: # Main menu options
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
                    "📁 *File/Text Conversion Menu*\n\n"
                    "1️⃣ PDF ➡️ Text\n"
                    "2️⃣ Text ➡️ PDF\n"
                    "3️⃣ PDF ➡️ Word\n"
                    "4️⃣ Text ➡️ Word\n\n"
                    "Type 1–4 to choose an option ✅"
                )
            elif user_text == "5":
                user_sessions[sender_number] = "awaiting_translation"
                response_text = "🌍 Translator active! Send text starting with `en:`, `hi:` etc."
            elif user_text == "6":
                user_sessions[sender_number] = "awaiting_weather"
                response_text = "🏙️ Enter your city (e.g., Delhi, Kanuru, Mumbai):"
            else:
                response_text = "🤔 I didn’t get that one.\nType *menu* to see options."

        if response_text:
            send_message(sender_number, response_text)

    except Exception as e:
        print(f"❌ ERROR: {e}")

    return "OK", 200

# === HELPER FUNCTIONS ===
def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")

def send_progress(to):
    send_message(to, "🔄 Loading...\n[█████-----] 50%")
    time.sleep(1.5)
    send_message(to, "✅ Done!")

def send_startup_effect(to):
    for step in ["👀 Booting up...", "🔌 Connecting circuits...", "💭 Warming up brain cells...", "🌈 AI Buddy is ready to roll! 🎉"]:
        send_message(to, step)
        time.sleep(1)

def send_welcome_message(to, name=None):
    greeting = f"🤖 *Welcome back, {name}!*" if name else "🤖 *Welcome to AI Buddy!*"
    menu_text = (
        "What can I help you with today?\n\n"
        "🧠 *1. Reminder* ⏰ — I’ll remember stuff so you don’t have to\n"
        "📖 *2. Grammar Fix* ✍️ — Send your messy sentences, I’ll clean ‘em\n"
        "🤖 *3. Ask Me Anything* 💬 — From doubts to jokes, I gotchu\n"
        "📁 *4. File/Text Conversion* 📄 — PDF ↔ Text ↔ Word\n"
        "🌍 *5. Translator* 🔁 — Type in `en:`, `hi:` etc., I’ll translate\n"
        "⛅ *6. Weather Bot* ☁️ — City name = instant forecast\n\n"
        "📌 *Reply with a number (1–6) to begin*\n"
        "🔁 *Type 'menu' any time to come back here*"
    )
    msg = f"{greeting}\n\n{menu_text}"
    send_message(to, msg)

def get_main_menu(user_number=None):
    icon = get_time_based_icon()
    user_data = load_user_data()
    name = user_data.get(user_number, {}).get("name", "")
    name_line = f"👤 *User:* {name}\n" if name else ""
    menu_text = (
        "What can I help you with today?\n\n"
        "🧠 *1. Reminder* ⏰ — I’ll remember stuff so you don’t have to\n"
        "📖 *2. Grammar Fix* ✍️ — Send your messy sentences, I’ll clean ‘em\n"
        "🤖 *3. Ask Me Anything* 💬 — From doubts to jokes, I gotchu\n"
        "📁 *4. File/Text Conversion* 📄 — PDF ↔ Text ↔ Word\n"
        "🌍 *5. Translator* 🔁 — Type in `en:`, `hi:` etc., I’ll translate\n"
        "⛅ *6. Weather Bot* ☁️ — City name = instant forecast\n\n"
        "📌 *Reply with a number (1–6) to begin*\n"
        "🔁 *Type 'menu' any time to come back here*"
    )
    return f"{icon} *AI-Buddy Main Menu* {icon}\n{name_line}\n{menu_text}"

def get_time_based_icon():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "🌞"
    elif 12 <= hour < 18: return "🌤️"
    elif 18 <= hour < 21: return "🌇"
    else: return "🌙"

def convert_text_to_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    text_encoded = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, text_encoded)
    filename = secure_filename(f"converted_{int(time.time())}.pdf")
    file_path = os.path.join("uploads", filename)
    pdf.output(file_path)
    return file_path
    
def convert_text_to_word(text):
    document = Document()
    document.add_paragraph(text)
    filename = secure_filename(f"converted_{int(time.time())}.docx")
    file_path = os.path.join("uploads", filename)
    document.save(file_path)
    return file_path

def extract_text_from_pdf_file(file_path):
    try:
        with fitz.open(file_path) as doc:
            text = "".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting PDF text: {e}")
        return ""

def send_file_to_user(to, file_path, mime_type, caption="Here is your file."):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    with open(file_path, "rb") as f:
        files = {'file': (os.path.basename(file_path), f, mime_type)}
        data = {"messaging_product": "whatsapp"}
        upload_response = requests.post(url, headers=headers, files=files, data=data)
    
    if upload_response.status_code != 200:
        print(f"Error uploading file: {upload_response.text}")
        return

    media_id = upload_response.json().get("id")
    if not media_id:
        return

    message_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "document",
        "document": {"id": media_id, "caption": caption}
    }
    requests.post(message_url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}, json=payload)

# === RUN APP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
