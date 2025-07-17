from flask import Flask, request
import requests
import os
import time
from datetime import datetime, timedelta
import json
from fpdf import FPDF
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import fitz  # PyMuPDF
import pytz
from docx import Document
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil import parser as date_parser

# --- Mock functions for other modules ---
def translate_text(text): return f"🌍 Translated text: `{text}`"
# --- End of mock functions ---


app = Flask(__name__)

# === CONFIG ===
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ranga123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GROK_API_KEY = os.environ.get("GROK_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

USER_DATA_FILE = "user_data.json"
user_sessions = {}

# --- Initialize the Scheduler ---
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

        if msg_type == "text":
            user_text = message["text"]["body"].strip()
            handle_text_message(user_text, sender_number, state)
        elif msg_type == "document":
            handle_document_message(message, sender_number, state)
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

def handle_text_message(user_text, sender_number, state):
    user_data = load_user_data()
    response_text = ""

    if user_text.lower() in ["hi", "hello", "hey", "start", "menu", "help", "options", "0"]:
        user_sessions.pop(sender_number, None)
        name = user_data.get(sender_number, {}).get("name")
        if not name:
            response_text = "👋 Hi there! To personalize your experience, what should I call you?"
            user_sessions[sender_number] = "awaiting_name"
        else:
            send_welcome_message(sender_number, name)
        if response_text: send_message(sender_number, response_text)
        return

    if state == "awaiting_name":
        name = user_text.split()[0].title()
        user_data[sender_number] = {"name": name}
        save_user_data(user_data)
        user_sessions.pop(sender_number, None)
        send_message(sender_number, f"✅ Got it! I’ll remember you as *{name}*.")
        time.sleep(1)
        send_welcome_message(sender_number, name)
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
            response_text = "❓ Please send a number from 1 to 4."
    else:
        if user_text == "1":
            user_sessions[sender_number] = "awaiting_reminder"
            response_text = "🕒 Sure, what's the reminder?\n\n_Examples:_\n- _Remind me to call John tomorrow at 4pm_\n- _Remind me about the team meeting on August 1st at 10am_"
        elif user_text == "2":
            user_sessions[sender_number] = "awaiting_grammar"
            response_text = "✍️ Send me the sentence or paragraph you want me to correct."
        elif user_text == "3":
            user_sessions[sender_number] = "awaiting_ai"
            response_text = "🤖 You can now chat with me! Ask me anything.\n\n_Type `menu` to exit this mode._"
        elif user_text == "4":
            user_sessions[sender_number] = "awaiting_conversion_choice"
            response_text = get_conversion_menu()
        elif user_text == "5":
            user_sessions[sender_number] = "awaiting_translation"
            response_text = "🌍 Translator active!\n\n_Example: `en:Hello world`_"
        elif user_text == "6":
            user_sessions[sender_number] = "awaiting_weather"
            response_text = "🏙️ Enter a city or location to get the current weather."
        else:
            response_text = "🤔 I didn't understand that. Please type *menu* to see the options."

    if response_text:
        send_message(sender_number, response_text)

# === UI, HELPERS, & LOGIC FUNCTIONS ===
def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message, "preview_url": False}}
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")

def ai_reply(prompt):
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured. This feature is disabled."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama3-8b-8192", "messages": [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": prompt}]}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"].strip()
        return "❌ Grok API returned a valid but empty reply."
    except requests.exceptions.RequestException as e:
        print(f"Grok API request error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now."
    except (KeyError, IndexError) as e:
        print(f"Grok API response parsing error: {e}")
        return "⚠️ There was an issue with the response from the AI service."

def correct_grammar_with_grok(text):
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured."
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a grammar correction assistant. Correct the grammar of the user's text and only return the corrected text, without any explanation or preamble."},
            {"role": "user", "content": text}
        ], "temperature": 0.7, "max_tokens": 1024
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        corrected_text = response.json()["choices"][0]["message"]["content"]
        return f"✅ Corrected:\n\n_{corrected_text}_"
    except Exception as e:
        print(f"Grok grammar error: {e}")
        return "❌ Sorry, the grammar correction service is unavailable."

# --- NEW: More flexible reminder function ---
def schedule_reminder(user_text, sender_number):
    try:
        # Sanitize the input to handle different phrasing
        text_to_parse = user_text.lower()
        starters = ["remind me to ", "remind me that ", "remind me about "]
        task_part = user_text
        for starter in starters:
            if text_to_parse.startswith(starter):
                task_part = user_text[len(starter):]
                break
        
        # Use fuzzy parsing to extract the time and the task
        run_time, Rtokens = date_parser.parse(task_part, fuzzy_with_tokens=True)
        task = " ".join(Rtokens).strip()

        # A common parsing error is including "on" or "at" at the end of the task
        if task.endswith(" on") or task.endswith(" at"):
            task = task[:-3].strip()

        if not task:
            return "❌ I couldn't figure out what you want to be reminded of. Please be more specific."

        # Make the time timezone-aware
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        
        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        if run_time < now:
            run_time += timedelta(days=1)

        reminder_message = f"⏰ *Reminder:* {task.capitalize()}"
        
        scheduler.add_job(
            func=send_message, trigger='date', run_date=run_time,
            args=[sender_number, reminder_message],
            id=f"{sender_number}-{task}-{run_time.timestamp()}",
            replace_existing=True
        )
        return f"✅ Got it! I'll remind you to *'{task}'* on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."

    except date_parser.ParserError:
        return "❌ I couldn't understand the date or time for the reminder. Please try again with a clear date and time."
    except Exception as e:
        print(f"❌ Reminder scheduling error: {e}")
        return "❌ Sorry, I had an unexpected error setting that reminder."


def get_welcome_message(name=""):
    name_line = f"👋 Welcome back, *{name}*!" if name else "👋 Welcome!"
    return (
        f"{name_line}\n\n"
        "How can I assist you today?\n\n"
        "1️⃣  *Set a Reminder* ⏰\n"
        "2️⃣  *Fix Grammar* ✍️\n"
        "3️⃣  *Ask AI Anything* 💬\n"
        "4️⃣  *File/Text Conversion* 📄\n"
        "5️⃣  *Translator* 🌍\n"
        "6️⃣  *Weather Forecast* ⛅\n\n"
        "📌 Reply with a number (1–6) to begin."
    )

def send_welcome_message(to, name):
    menu_text = get_welcome_message(name)
    send_message(to, menu_text)

def get_conversion_menu():
    return (
        "📁 *File/Text Conversion Menu*\n\n"
        "1️⃣ PDF ➡️ Text\n"
        "2️⃣ Text ➡️ PDF\n"
        "3️⃣ PDF ➡️ Word\n"
        "4️⃣ Text ➡️ Word\n\n"
        "Reply with a number (1-4)."
    )

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

def get_weather(city):
    if not OPENWEATHER_API_KEY:
        return "❌ The OpenWeatherMap API key is not configured. This feature is disabled."
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        icon_code = data["weather"][0]["icon"]
        emoji_map = {
            "01": "☀️", "02": "⛅️", "03": "☁️", "04": "☁️",
            "09": "🌧️", "10": "🌦️", "11": "⛈️", "13": "❄️", "50": "🌫️"
        }
        emoji = emoji_map.get(icon_code[:2], "🌡️")
        description = data["weather"][0]["description"].title()
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        return (
            f"*{data['name']} Weather Report* {emoji}\n"
            "•----------------------------------•\n\n"
            f"*{description}*\n\n"
            f"🌡️ *Temperature:* {temp}°C\n"
            f"   _Feels like: {feels_like}°C_\n\n"
            f"💧 *Humidity:* {humidity}%\n\n"
            "Stay safe! 🌦️"
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"⚠️ City not found: '{city.title()}'."
        else: print(f"Weather API HTTP error: {e}")
        return "❌ Oops! A weather service error occurred."
    except Exception as e:
        print(f"Weather function error: {e}")
        return "❌ An unexpected error occurred while fetching weather."

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

# === RUN APP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
