from flask import Flask, request
import requests
import os
import time
from datetime import datetime, timedelta
import json
import re
from fpdf import FPDF
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import fitz  # PyMuPDF
import pytz
from docx import Document
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil import parser as date_parser
import pandas as pd
from currency import convert_currency # Import our function

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
    user_text_lower = user_text.lower()
    
    expense_keywords = ['spent', 'paid', 'bought', 'expense', 'cost']
    export_keywords = ['excel', 'sheet', 'report', 'export']
    
    if any(keyword in user_text_lower for keyword in export_keywords):
        send_message(sender_number, "📊 Generating your expense report...")
        file_path = export_expenses_to_excel(sender_number)
        if file_path:
            send_file_to_user(sender_number, file_path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Here is your expense report.xlsx")
            os.remove(file_path)
        else:
            send_message(sender_number, "You have no expenses to export yet.")
        return

    if any(keyword in user_text_lower for keyword in expense_keywords):
        send_message(sender_number, "Analyzing expense...")
        expenses = parse_expense_with_grok(user_text)
        if expenses:
            confirmations = []
            for expense in expenses:
                cost = expense.get('cost')
                if isinstance(cost, (int, float)):
                    confirmation = log_expense(
                        sender_number, 
                        cost, 
                        expense.get('item'), 
                        expense.get('place'), 
                        expense.get('timestamp')
                    )
                    confirmations.append(confirmation)
                else:
                    confirmations.append(f"❓ Could not log '{expense.get('item')}' - cost is unclear.")
            send_message(sender_number, "\n".join(confirmations))
        else:
            send_message(sender_number, "Sorry, I couldn't understand that as an expense. Try being more specific about the cost and item.")
        return

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
        user_data[sender_number] = {"name": name, "expenses": []}
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
    
    # --- NEW: AI-powered state for currency conversion ---
    elif state == "awaiting_currency_conversion":
        send_message(sender_number, "Analysing your request...")
        conversions = parse_currency_with_grok(user_text)
        if conversions:
            results = [convert_currency(c.get('amount'), c.get('from_currency'), c.get('to_currency')) for c in conversions]
            response_text = "\n\n".join(results)
        else:
            response_text = "❌ Sorry, I couldn't understand that conversion request. Please be specific about the amount and 3-letter currency codes (e.g., USD, INR)."
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
    else: # Main Menu selections
        if user_text == "1":
            user_sessions[sender_number] = "awaiting_reminder"
            response_text = "🕒 Sure, what's the reminder?\n\n_Examples:_\n- _Remind me to call John tomorrow at 4pm_\n- _I have a meeting on August 1st at 10am_"
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
        elif user_text == "7":
            user_sessions[sender_number] = "awaiting_currency_conversion"
            response_text = "💱 *Currency Converter*\n\nAsk me to convert currencies naturally!\n\n_Examples:_\n- _How much is 50 dollars in indian rupees?_\n- _convert 20 eur to usd and 100 gbp to jpy_"
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

def schedule_reminder(user_text, sender_number):
    try:
        send_message(sender_number, "Figuring out your reminder...")
        task, timestamp_str = parse_reminder_with_grok(user_text)
        if not task or not timestamp_str:
            return "❌ I couldn't quite understand that reminder. Could you try phrasing it differently?"
        run_time = date_parser.parse(timestamp_str)
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)
        if run_time < now:
            return f"❌ The time for your reminder ({run_time.strftime('%I:%M %p')}) seems to be in the past."
        reminder_message = f"⏰ *Reminder:* {task.capitalize()}"
        scheduler.add_job(
            func=send_message, trigger='date', run_date=run_time,
            args=[sender_number, reminder_message],
            id=f"{sender_number}-{task}-{run_time.timestamp()}",
            replace_existing=True
        )
        return f"✅ Got it! I'll remind you to *'{task}'* on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
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
        "6️⃣  *Weather Forecast* ⛅\n"
        "7️⃣  *Currency Converter* 💱\n\n"
        "📌 Reply with a number (1–7) to begin.\n\n"
        "💡 _Hidden Feature: I'm also your personal expense tracker! Just tell me what you spent and ask for your data anytime with `Give Excel Sheet`._"
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

# === AI PARSING FUNCTIONS ===
def parse_expense_with_grok(text):
    if not GROK_API_KEY:
        print("Grok API key not set for expense parsing.")
        return None
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
    You are an expert expense parsing assistant. Your task is to extract all expenses from the user's text.
    The text is: "{text}"
    Extract the cost (as a number), the item purchased, the place of purchase (if mentioned), and the timestamp (if mentioned).
    Return the result as a JSON object with a single key "expenses" which is an array of objects. 
    Each object must have keys "cost", "item", "place", and "timestamp".
    If a place or timestamp is not mentioned, set its value to null.
    Only return the JSON object, with no other text or explanation.
    """
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("expenses")
    except Exception as e:
        print(f"Grok expense parsing error: {e}")
        return None

def parse_reminder_with_grok(text):
    if not GROK_API_KEY:
        return None, None
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
    You are a task and time extraction assistant. From the user's text, identify the core task and the specific timestamp.
    The current date is {datetime.now().strftime('%Y-%m-%d %A')}.
    The user's text is: "{text}"
    Return a JSON object with two keys: "task" (the what) and "timestamp" (the when).
    The timestamp should be in a machine-readable format like 'YYYY-MM-DD HH:MM:SS'.
    Only return the JSON object.
    """
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("task"), result_data.get("timestamp")
    except Exception as e:
        print(f"Grok reminder parsing error: {e}")
        return None, None

def parse_currency_with_grok(text):
    if not GROK_API_KEY:
        return None
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
    You are an expert currency conversion parser. From the user's text, extract all requests to convert money.
    The user's text is: "{text}"
    Return a JSON object with a single key "conversions" which is an array of objects. 
    Each object must have keys "amount", "from_currency", and "to_currency".
    Use standard 3-letter currency codes (e.g., USD, INR, EUR).
    Only return the JSON object.
    """
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("conversions")
    except Exception as e:
        print(f"Grok currency parsing error: {e}")
        return None

# === EXPENSE TRACKER FUNCTIONS ===
def log_expense(sender_number, amount, item, place=None, timestamp_str=None):
    all_data = load_user_data()
    user_info = all_data.setdefault(sender_number, {"name": "", "expenses": []})
    
    if timestamp_str:
        try:
            expense_time = date_parser.parse(timestamp_str)
            tz = pytz.timezone('Asia/Kolkata')
            if expense_time.tzinfo is None:
                expense_time = tz.localize(expense_time)
        except (date_parser.ParserError, pytz.exceptions.AmbiguousTimeError):
            expense_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    else:
        expense_time = datetime.now(pytz.timezone('Asia/Kolkata'))

    new_expense = {
        "cost": amount, "item": item,
        "place": place if place else "N/A",
        "timestamp": expense_time.isoformat()
    }
    user_info.setdefault("expenses", []).append(new_expense)
    save_user_data(all_data)
    log_message = f"✅ Logged: *₹{amount:.2f}* for *{item.title()}*"
    if place and place != "N/A":
        log_message += f" at *{place.title()}*"
    return log_message

def export_expenses_to_excel(sender_number):
    all_data = load_user_data()
    user_expenses = all_data.get(sender_number, {}).get("expenses", [])
    if not user_expenses:
        return None
    df = pd.DataFrame(user_expenses)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['Date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    df['Time'] = df['timestamp'].dt.strftime('%I:%M %p')
    df = df[['Date', 'Time', 'item', 'place', 'cost']]
    df.rename(columns={'item': 'Item', 'place': 'Place', 'cost': 'Cost (₹)'}, inplace=True)
    file_path = os.path.join("uploads", f"expenses_{sender_number}.xlsx")
    df.to_excel(file_path, index=False, engine='openpyxl')
    return file_path

# === RUN APP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
