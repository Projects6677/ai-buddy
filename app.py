# app.py

from flask import Flask, request, redirect, session, url_for
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
from werkzeug.middleware.proxy_fix import ProxyFix

from currency import convert_currency
from grok_ai import (
    ai_reply,
    correct_grammar_with_grok,
    parse_expense_with_grok,
    parse_reminder_with_grok,
    parse_currency_with_grok,
    is_expense_intent,
    analyze_email_subject,
    edit_email_body,
    write_email_body_with_grok,
    translate_with_grok
)
from email_sender import send_email
from services import get_daily_quote, get_on_this_day_facts
from google_calendar_integration import get_google_auth_flow, get_credentials, save_credentials, create_google_calendar_event

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.secret_key = os.urandom(24)

# === CONFIG ===
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ranga123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GROK_API_KEY = os.environ.get("GROK_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

USER_DATA_FILE = "user_data.json"
user_sessions = {}

# === UPDATED SCHEDULER CONFIG FOR RENDER ===
# Using a background scheduler. For production on platforms like Render,
# it's highly recommended to use a persistent job store like a database (e.g., PostgreSQL)
# instead of the default memory store to prevent scheduled jobs from being lost on worker restarts.
# For simplicity in this example, we will stick to the BackgroundScheduler.
# See the previous explanation for how to configure a persistent job store if needed.
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

# --- NEW: GOOGLE AUTHENTICATION ROUTES ---
@app.route('/google-auth')
def google_auth():
    sender_number = request.args.get('state')
    session['sender_number'] = sender_number # Store sender_number in session
    flow = get_google_auth_flow()
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=sender_number
    )
    return redirect(authorization_url)

@app.route('/google-auth/callback')
def google_auth_callback():
    state = request.args.get('state')
    sender_number = state # The state is the user's phone number

    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    save_credentials(sender_number, credentials)

    # Let the user know it was successful
    send_message(sender_number, "✅ Your Google Calendar has been successfully connected! You can now set reminders and they will be added to your calendar.")

    user_sessions.pop(sender_number, None) # Clean up session state
    return "Authentication successful! You can return to WhatsApp."


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

        original_filename = "attached_file"
        if 'document' in media_info:
            original_filename = media_info['document'].get('filename', original_filename)

        download_response = requests.get(media_url, headers=headers)
        download_response.raise_for_status()

        temp_filename = secure_filename(original_filename)
        if not temp_filename:
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
    filename = message["document"].get("filename", "attached_file")

    if isinstance(state, dict) and state.get("state") == "awaiting_email_attachment":
        send_message(sender_number, f"Got it. Attaching `{filename}` to your email...")
        downloaded_path = download_media_from_whatsapp(media_id)
        if downloaded_path:
            # Initialize attachment list if it doesn't exist
            if "attachment_paths" not in state:
                state["attachment_paths"] = []
            state["attachment_paths"].append(downloaded_path)

            state["state"] = "awaiting_more_attachments" # New state
            user_sessions[sender_number] = state
            response_text = f"✅ File attached successfully!\n\nType *'done'* when you have finished attaching files, or upload another document."
            send_message(sender_number, response_text)
        else:
            send_message(sender_number, "❌ Sorry, I couldn't download your attachment. Please try again.")
        return

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

    # --- Smart Command Handling ---
    export_keywords = ['excel', 'sheet', 'report', 'export']

    if any(keyword in user_text_lower for keyword in export_keywords) and not state:
        send_message(sender_number, "📊 Generating your expense report...")
        file_path = export_expenses_to_excel(sender_number)
        if file_path:
            send_file_to_user(sender_number, file_path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Here is your expense report.xlsx")
            os.remove(file_path)
        else:
            send_message(sender_number, "You have no expenses to export yet.")
        return

    if is_expense_intent(user_text) and not state:
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
    elif state == "awaiting_email_recipient":
        recipients = [email.strip() for email in user_text.split(',')]
        valid_recipients = [email for email in recipients if re.match(r"[^@]+@[^@]+\.[^@]+", email)]
        if valid_recipients:
            user_sessions[sender_number] = {"state": "awaiting_email_subject", "recipients": valid_recipients}
            response_text = f"✅ Got recipient(s). Now, what should the subject of the email be?"
        else:
            response_text = "⚠️ I couldn't find any valid email addresses. Please try again."
    elif isinstance(state, dict) and state.get("state") == "awaiting_email_subject":
        subject = user_text
        send_message(sender_number, "👍 Great subject. Let me think of some follow-up questions...")
        questions = analyze_email_subject(subject)
        if questions:
            user_sessions[sender_number] = {"state": "gathering_email_details", "recipients": state["recipients"], "subject": subject, "questions": questions, "answers": [], "current_question_index": 0}
            response_text = questions[0]
        else:
            user_sessions[sender_number] = {"state": "awaiting_email_prompt_fallback", "recipients": state["recipients"], "subject": subject}
            response_text = "Okay, I'll just need one main prompt. What should the email be about?"
    elif isinstance(state, dict) and state.get("state") == "gathering_email_details":
        state["answers"].append(user_text)
        state["current_question_index"] += 1
        if state["current_question_index"] < len(state["questions"]):
            response_text = state["questions"][state["current_question_index"]]
            user_sessions[sender_number] = state
        else:
            send_message(sender_number, "🤖 Got all the details. Writing your email with AI, please wait...")
            full_prompt = f"Write an email with the subject '{state['subject']}'. Use the following details:\n"
            for i, q in enumerate(state["questions"]):
                full_prompt += f"- {q}: {state['answers'][i]}\n"
            email_body = write_email_body_with_grok(full_prompt)
            if "❌" in email_body:
                response_text = email_body
                user_sessions.pop(sender_number, None)
            else:
                user_sessions[sender_number] = {"state": "awaiting_email_edit", "recipients": state["recipients"], "subject": state["subject"], "body": email_body}
                response_text = f"Here is the draft:\n\n---\n{email_body}\n---\n\n_You can ask for changes, type *'attach'* to add a file, or type *'send'* to approve._"
    elif isinstance(state, dict) and state.get("state") == "awaiting_email_prompt_fallback":
        prompt = user_text
        send_message(sender_number, "🤖 Writing your email with AI, please wait...")
        email_body = write_email_body_with_grok(prompt)
        if "❌" in email_body:
            response_text = email_body
            user_sessions.pop(sender_number, None)
        else:
            user_sessions[sender_number] = {"state": "awaiting_email_edit", "recipients": state["recipients"], "subject": state["subject"], "body": email_body}
            response_text = f"Here is the draft:\n\n---\n{email_body}\n---\n\n_You can ask for changes, type *'attach'* to add a file, or type *'send'* to approve._"

    elif isinstance(state, dict) and state.get("state") == "awaiting_more_attachments":
        if user_text_lower == "done":
            state["state"] = "awaiting_email_edit"
            user_sessions[sender_number] = state
            num_files = len(state.get("attachment_paths", []))
            response_text = f"✅ Okay, {num_files} file(s) are attached. You can now review the draft, ask for more changes, or type *'send'*."
        else:
            response_text = "Please upload another file, or type *'done'* to finish."

    # === START: FULLY REVISED EMAIL EDIT/SEND/SCHEDULE LOGIC ===
    elif isinstance(state, dict) and state.get("state") == "awaiting_email_edit":
        # Case 1: User wants to send the email immediately
        if user_text_lower in ["send", "send it", "approve", "ok send", "yes send"]:
            send_message(sender_number, "✅ Okay, sending the email now...")
            attachment_paths = state.get("attachment_paths", [])
            response_text = send_email(state["recipients"], state["subject"], state["body"], attachment_paths)
            for path in attachment_paths:
                if os.path.exists(path): os.remove(path)
            user_sessions.pop(sender_number, None)
        
        # Case 2: User wants to attach a file
        elif user_text_lower == "attach":
            state["state"] = "awaiting_email_attachment"
            user_sessions[sender_number] = state
            response_text = "📎 Please upload the first file you want to attach."
        
        # Case 3: User might be trying to schedule or edit the email
        else:
            # Use AI to figure out if it's a schedule command
            _, timestamp_str = parse_reminder_with_grok(user_text)

            # If AI finds a valid time, it's a schedule command
            if timestamp_str:
                try:
                    tz = pytz.timezone('Asia/Kolkata')
                    now = datetime.now(tz)
                    run_time = date_parser.parse(timestamp_str)
                    
                    if run_time.tzinfo is None:
                        run_time = tz.localize(run_time)
                    
                    if run_time < now:
                        response_text = f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) is in the past. Please specify a future time."
                    else:
                        attachment_paths = state.get("attachment_paths", [])
                        scheduler.add_job(
                            func=send_email, 
                            trigger='date', 
                            run_date=run_time, 
                            args=[state["recipients"], state["subject"], state["body"], attachment_paths]
                        )
                        response_text = f"👍 Scheduled! The email will be sent on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
                    
                    user_sessions.pop(sender_number, None)

                except (date_parser.ParserError, ValueError) as e:
                    print(f"Error parsing timestamp from Grok: {e}")
                    response_text = "I understood you want to schedule the email, but had trouble with the exact time. Please try rephrasing the time."

            # If it's not a schedule command, assume it's an edit instruction
            else:
                send_message(sender_number, "✏️ Applying your changes, please wait...")
                new_body = edit_email_body(state["body"], user_text)
                if new_body:
                    user_sessions[sender_number]["body"] = new_body
                    response_text = f"Here is the updated draft:\n\n---\n{new_body}\n---\n\n_Ask for more changes, type *'attach'* for a file, or *'send'*._"
                else:
                    response_text = "Sorry, I couldn't apply that change. Please try rephrasing your instruction."
    # === END: FULLY REVISED EMAIL LOGIC ===

    elif state == "awaiting_reminder":
        task, timestamp_str = parse_reminder_with_grok(user_text)
        if not task or not timestamp_str:
            response_text = "❌ I couldn't understand the reminder. Please try again, for example: 'Remind me to call Mom tomorrow at 5 PM'."
        else:
            user_sessions[sender_number] = {
                "state": "awaiting_reminder_type_choice",
                "task": task,
                "timestamp_str": timestamp_str
            }
            response_text = (
                "Got it. How would you like me to remind you?\n\n"
                "1️⃣ Send a WhatsApp Message\n"
                "2️⃣ Add to Google Calendar"
            )

    elif isinstance(state, dict) and state.get("state") == "awaiting_reminder_type_choice":
        choice = user_text.strip()
        task = state["task"]
        timestamp_str = state["timestamp_str"]

        if choice == "1": # WhatsApp Reminder
            response_text = schedule_whatsapp_reminder(task, timestamp_str, sender_number)
            user_sessions.pop(sender_number, None)
        elif choice == "2": # Google Calendar Reminder
            credentials = get_credentials(sender_number)
            if not credentials:
                auth_url = url_for('google_auth', state=sender_number, _external=True)
                response_text = (
                    "To connect to your calendar, please use the link below to grant permission. You only need to do this once.\n\n"
                    f"🔗 [Click here to authorize]({auth_url})\n\n"
                    "After authorizing, please set your reminder again."
                )
                user_sessions.pop(sender_number, None)
            else:
                try:
                    tz = pytz.timezone('Asia/Kolkata')
                    run_time = date_parser.parse(timestamp_str)
                    if run_time.tzinfo is None:
                        run_time = tz.localize(run_time)
                    response_text = create_google_calendar_event(credentials, task, run_time)
                    user_sessions.pop(sender_number, None)
                except Exception as e:
                    print(f"Error parsing timestamp for Google Calendar: {e}")
                    response_text = "❌ An unexpected error occurred while setting your calendar event."
        else:
            response_text = "Please choose a valid option by replying with *1* or *2*."


    elif state == "awaiting_grammar":
        response_text = correct_grammar_with_grok(user_text)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_ai":
        response_text = ai_reply(user_text)
    elif state == "awaiting_translation":
        response_text = translate_with_grok(user_text)
    elif state == "awaiting_weather":
        response_text = get_weather(user_text)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_currency_conversion":
        send_message(sender_number, "Analysing your request...")
        conversions = parse_currency_with_grok(user_text)
        if conversions:
            results = [convert_currency(c.get('amount'), c.get('from_currency'), c.get('to_currency')) for c in conversions]
            response_text = "\n\n".join(results)
        else:
            response_text = "❌ Sorry, I couldn't understand that conversion request."
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
            response_text = "🕒 Sure, what's the reminder?\n\n_Examples:_\n- _Remind me to call John tomorrow at 4pm_"
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
            response_text = "🌍 *AI Translator Active!*\n\nHow can I help you translate today?\n\n_Examples:_\n- _Translate 'I love programming' to French._\n- _How do you say 'Where is the library?' in Spanish?_"
        elif user_text == "6":
            user_sessions[sender_number] = "awaiting_weather"
            response_text = "🏙️ Enter a city or location to get the current weather."
        elif user_text == "7":
            user_sessions[sender_number] = "awaiting_currency_conversion"
            response_text = "💱 *Currency Converter*\n\nAsk me to convert currencies naturally!"
        elif user_text == "8":
            user_sessions[sender_number] = "awaiting_email_recipient"
            response_text = "📧 *AI Email Assistant*\n\nWho are the recipients? Please enter their email addresses, separated by commas."
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

def get_welcome_message(name=""):
    name_line = f"👋 Welcome back, *{name}*!" if name else "👋 Welcome!"
    return (
        f"{name_line}\n\n"
        "How can I assist you today?\n\n"
        "1️⃣  *Set a Reminder* (WhatsApp or Google Calendar) ⏰\n"
        "2️⃣  *Fix Grammar* ✍️\n"
        "3️⃣  *Ask AI Anything* �\n"
        "4️⃣  *File/Text Conversion* 📄\n"
        "5️⃣  *Translator* 🌍\n"
        "6️⃣  *Weather Forecast* ⛅\n"
        "7️⃣  *Currency Converter* 💱\n"
        "8️⃣  *AI Email Assistant* 📧\n\n"
        "📌 Reply with a number (1–8) to begin.\n\n"
        "💡 _You'll automatically receive a Daily Briefing with a quote and historical facts every morning!_\n\n"
        "✨ _Hidden Feature: I'm also an AI expense tracker! Just tell me what you spent and ask for your data anytime with `Give Excel Sheet`._"
    )

def send_welcome_message(to, name):
    menu_text = get_welcome_message(name)
    send_message(to, menu_text)

def schedule_whatsapp_reminder(task, timestamp_str, sender_number):
    try:
        tz = pytz.timezone('Asia/Kolkata')
        run_time = date_parser.parse(timestamp_str)

        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        if run_time < now:
            return f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) seems to be in the past. Please specify a future time."

        scheduler.add_job(
            func=send_message,
            trigger='date',
            run_date=run_time,
            args=[sender_number, f"⏰ Reminder: {task}"],
            id=f"reminder_{sender_number}_{int(run_time.timestamp())}",
            replace_existing=True
        )
        return f"✅ Reminder set! I will send you a WhatsApp message to '{task}' on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
    except Exception as e:
        print(f"An unexpected error occurred in schedule_whatsapp_reminder: {e}")
        return "❌ An unexpected error occurred while setting your reminder."

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
        emoji_map = { "01": "☀️", "02": "⛅️", "03": "☁️", "04": "☁️", "09": "🌧️", "10": "🌦️", "11": "⛈️", "13": "❄️", "50": "🌫️" }
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

    if expense_time.date() != datetime.now(pytz.timezone('Asia/Kolkata')).date():
        log_message += f" on *{expense_time.strftime('%B %d')}*"

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

def send_daily_briefing():
    print(f"--- Running Daily Briefing Job at {datetime.now()} ---")
    all_users = load_user_data()
    if not all_users:
        print("No users found in user_data.json. Skipping job.")
        return

    quote = get_daily_quote()
    facts = get_on_this_day_facts()

    briefing_message = (
        "☀️ *Good Morning! Here is your Daily Briefing.*\n\n"
        "💡 *Quote of the Day*\n"
        f"_{quote}_\n\n"
        "🗓️ *On This Day in History*\n"
        f"{facts}"
    )

    print(f"Found {len(all_users)} user(s) to send the briefing to.")
    for user_id in all_users.keys():
        print(f"Sending daily briefing to {user_id}")
        send_message(user_id, briefing_message)
        time.sleep(1)

    print("--- Daily Briefing Job Finished ---")

def notify_users_on_startup():
    print("--- Checking for users to notify about update ---")
    all_users = load_user_data()
    if not all_users:
        print("No users found, skipping startup notifications.")
        return

    update_message = (
        "Hello! AI Buddy has just been updated. 🤖\n\n"
        "To ensure everything is synced up correctly, please send a new message like *'hi'* or *'menu'* to continue."
    )

    print(f"Found {len(all_users)} user(s). Preparing to send update notifications...")
    for user_id in all_users.keys():
        print(f"Sending update notification to {user_id}")
        send_message(user_id, update_message)
        time.sleep(1)

    print("--- Finished sending startup notifications ---")

# --- RUN APP ---
if __name__ == '__main__':
    # Notify users that the bot has been updated and to re-engage
    notify_users_on_startup()

    # Schedule the daily briefing job
    scheduler.add_job(
        func=send_daily_briefing,
        trigger='cron',
        hour=8,
        minute=0,
        timezone='Asia/Kolkata',
        id='daily_briefing_job',
        replace_existing=True
    )

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
