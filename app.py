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
from pymongo import MongoClient
from urllib.parse import urlparse
import pickle
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


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
    translate_with_grok,
    analyze_document_context, 
    get_contextual_ai_response,
    is_document_followup_question
)
from email_sender import send_email
from services import get_daily_quote, get_tech_headline, get_briefing_weather, get_tech_tip, get_email_summary
from google_calendar_integration import get_google_auth_flow, create_google_calendar_event
from reminders import schedule_reminder
from messaging import send_message, send_template_message, send_interactive_menu, send_conversion_menu
from document_processor import get_text_from_file
from weather import get_weather


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.secret_key = os.urandom(24)

# === CONFIGURATION ===
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ranga123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GROK_API_KEY = os.environ.get("GROK_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY")
MONGO_URI = os.environ.get("MONGO_URI")
DEV_PHONE_NUMBER = os.environ.get("DEV_PHONE_NUMBER")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")


# --- DATABASE CONNECTION ---
client = MongoClient(MONGO_URI)
db = client.ai_buddy_db
users_collection = db.users

user_sessions = {}

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
scheduler.start()


if not os.path.exists("uploads"):
    os.makedirs("uploads")

# === DATABASE HELPER FUNCTIONS ===
def get_user_from_db(sender_number):
    """Fetches a single user's data from the database."""
    return users_collection.find_one({"_id": sender_number})

def create_or_update_user_in_db(sender_number, data):
    """Saves or updates a user's data in the database."""
    users_collection.update_one({"_id": sender_number}, {"$set": data}, upsert=True)

# --- MODIFICATION START ---
def get_all_users_from_db():
    """Fetches all users (ID, name, and connection status) from the database."""
    return users_collection.find({}, {"_id": 1, "name": 1, "is_google_connected": 1})
# --- MODIFICATION END ---

def delete_all_users_from_db():
    """Deletes all user data from the database."""
    return users_collection.delete_many({})

def count_users_in_db():
    """Counts the total number of users in the database."""
    return users_collection.count_documents({})

# --- GOOGLE CREDENTIALS HELPER FUNCTIONS ---
def save_credentials_to_db(sender_number, credentials):
    """Saves pickled Google credentials to the user's document in MongoDB."""
    pickled_creds = pickle.dumps(credentials)
    create_or_update_user_in_db(sender_number, {"google_credentials": pickled_creds, "is_google_connected": True})

def get_credentials_from_db(sender_number):
    """
    Gets Google credentials from the database and refreshes them if needed.
    """
    user_data = get_user_from_db(sender_number)
    if not user_data or "google_credentials" not in user_data:
        return None

    creds = pickle.loads(user_data["google_credentials"])

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials_to_db(sender_number, creds)

    if creds and creds.valid:
        return creds
    
    return None

# === ROUTES ===
@app.route('/')
def home():
    return "WhatsApp AI Assistant is Live!"

@app.route('/google-auth')
def google_auth():
    sender_number = request.args.get('state')
    session['sender_number'] = sender_number
    flow = get_google_auth_flow()
    authorization_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', state=sender_number)
    return redirect(authorization_url)

@app.route('/google-auth/callback')
def google_auth_callback():
    state = request.args.get('state')
    sender_number = state
    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    save_credentials_to_db(sender_number, credentials)
    
    send_message(sender_number, "✅ Your Google account has been successfully connected!")
    user_sessions.pop(sender_number, None)
    return "Authentication successful! You can return to WhatsApp."

@app.route('/test-briefing')
def trigger_daily_briefing():
    secret = request.args.get('secret')
    if not ADMIN_SECRET_KEY or secret != ADMIN_SECRET_KEY:
        return "Unauthorized: Invalid or missing secret key.", 401
    send_daily_briefing()
    return "✅ Daily briefing has been sent to all users.", 200

@app.route('/notify-update')
def trigger_update_notification():
    secret = request.args.get('secret')
    features = request.args.get('features')
    if not ADMIN_SECRET_KEY or secret != ADMIN_SECRET_KEY:
        return "Unauthorized: Invalid or missing secret key.", 401
    if not features:
        return "Bad Request: Please provide a 'features' parameter.", 400
    scheduler.add_job(func=send_update_notification_to_all_users, trigger='date', run_date=datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(seconds=2), args=[features])
    return f"✅ Success! Update notification scheduled for: '{features}'", 200

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
        return file_path, media_info.get('mime_type')
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading media: {e}")
        return None, None

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

        if msg_type == "interactive":
            interactive_data = message["interactive"]
            if interactive_data["type"] == "list_reply":
                selection_id = interactive_data["list_reply"]["id"]
                handle_text_message(selection_id, sender_number, state)
            elif interactive_data["type"] == "button_reply":
                selection_id = interactive_data["button_reply"]["id"]
                handle_text_message(selection_id, sender_number, state)
        elif msg_type == "text":
            user_text = message["text"]["body"].strip()
            handle_text_message(user_text, sender_number, state)
        elif msg_type in ["document", "image"]:
            handle_document_message(message, sender_number, state)
        else:
            send_message(sender_number, "🤔 Sorry, I can only process text, documents, and images at the moment.")

    except Exception as e:
        print(f"❌ Unhandled Error: {e}")
    return "OK", 200

# === MESSAGE HANDLERS ===
def handle_document_message(message, sender_number, state):
    media_id = message.get(message['type'], {}).get('id')
    if not media_id:
        send_message(sender_number, "❌ I couldn't find the file in your message.")
        return

    if isinstance(state, dict) and state.get("state") == "awaiting_email_attachment":
        filename = message.get('document', {}).get('filename', 'attached_file')
        send_message(sender_number, f"Got it. Attaching `{filename}` to your email...")
        downloaded_path, _ = download_media_from_whatsapp(media_id)
        if downloaded_path:
            if "attachment_paths" not in state:
                state["attachment_paths"] = []
            state["attachment_paths"].append(downloaded_path)
            state["state"] = "awaiting_more_attachments"
            user_sessions[sender_number] = state
            response_text = f"✅ File attached successfully!\n\nType *'done'* when you have finished attaching files, or upload another document."
            send_message(sender_number, response_text)
        else:
            send_message(sender_number, "❌ Sorry, I couldn't download your attachment. Please try again.")
        return

    downloaded_path, mime_type = download_media_from_whatsapp(media_id)
    if not downloaded_path:
        send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
        return

    if state == "awaiting_pdf_to_text":
        extracted_text = get_text_from_file(downloaded_path, mime_type)
        response = extracted_text if extracted_text else "Could not find any readable text in the PDF."
        send_message(sender_number, response)
        user_sessions.pop(sender_number, None)
        if os.path.exists(downloaded_path): os.remove(downloaded_path)
        return

    elif state == "awaiting_pdf_to_docx":
        output_docx_path = downloaded_path + ".docx"
        cv = Converter(downloaded_path)
        cv.convert(output_docx_path, start=0, end=None)
        cv.close()
        send_file_to_user(sender_number, output_docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
        if os.path.exists(output_docx_path): os.remove(output_docx_path)
        user_sessions.pop(sender_number, None)
        if os.path.exists(downloaded_path): os.remove(downloaded_path)
        return

    send_message(sender_number, "📄 Got your file! Analyzing it with AI...")
    
    extracted_text = get_text_from_file(downloaded_path, mime_type)
    if not extracted_text:
        send_message(sender_number, "❌ I couldn't find any readable text in that file.")
        if os.path.exists(downloaded_path): os.remove(downloaded_path)
        return

    analysis = analyze_document_context(extracted_text)
    if not analysis:
        send_message(sender_number, "🤔 I analyzed the document, but I'm not sure what to do with it.")
        if os.path.exists(downloaded_path): os.remove(downloaded_path)
        return
        
    doc_type = analysis.get("doc_type")
    data = analysis.get("data", {})

    user_sessions[sender_number] = {
        "state": "awaiting_document_question",
        "document_text": extracted_text,
        "doc_type": doc_type,
        "data": data
    }

    if doc_type == "resume":
        response = "I've analyzed your resume. I can give you a score and feedback, or you can ask me specific questions about it (e.g., 'critique my resume' or 'what are my key skills?')."
    elif doc_type == "project_plan":
        response = "I've read your project plan. You can now ask me questions about it (e.g., 'what is the main goal?' or 'summarize the tech stack')."
    elif doc_type == "meeting_invite":
        task = data.get("task", "this event")
        response = f"I see this is an invitation for '{task}'. Would you like me to schedule it for you?"
    elif doc_type == "q_and_a":
        response = "I've processed the questions in your document. You can ask me to 'answer all questions', or ask about a specific one."
    else:
        response = "I've finished reading your document. You can ask me to summarize it, or ask any specific questions you have about the content."

    send_message(sender_number, response)

    if os.path.exists(downloaded_path):
        os.remove(downloaded_path)

def handle_text_message(user_text, sender_number, state):
    user_text_lower = user_text.lower()
    menu_commands = ["start", "menu", "help", "options", "0"]
    if user_text_lower in menu_commands:
        user_sessions.pop(sender_number, None)
        user_data = get_user_from_db(sender_number)
        if not user_data:
            response_text = "👋 Hi there! To personalize your experience, what should I call you?"
            user_sessions[sender_number] = "awaiting_name"
            send_message(sender_number, response_text)
        else:
            send_welcome_message(sender_number, user_data.get("name"))
        return
    
    if user_text.startswith(".dev"):
        if not DEV_PHONE_NUMBER or sender_number != DEV_PHONE_NUMBER:
            send_message(sender_number, "❌ Unauthorized: This is a developer-only command.")
            return
        
        parts = user_text.split()
        if len(parts) < 3:
            send_message(sender_number, "❌ Invalid command format.\nUse: `.dev <secret_key> <feature_list>`")
            return
        
        command, key, features = parts[0], parts[1], " ".join(parts[2:])

        if not ADMIN_SECRET_KEY or key != ADMIN_SECRET_KEY:
            send_message(sender_number, "❌ Invalid admin secret key.")
            return

        scheduler.add_job(func=send_update_notification_to_all_users, trigger='date', run_date=datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(seconds=2), args=[features])
        send_message(sender_number, f"✅ Success! Update notification job scheduled for all users.\n\n*Features:* {features}")
        return

    elif user_text.startswith(".test"):
        if not DEV_PHONE_NUMBER or sender_number != DEV_PHONE_NUMBER:
            send_message(sender_number, "❌ Unauthorized: This is a developer-only command.")
            return

        parts = user_text.split()
        if len(parts) != 2:
            send_message(sender_number, "❌ Invalid format. Use: `.test <passcode>`")
            return

        passcode = parts[1]
        if not ADMIN_SECRET_KEY or passcode != ADMIN_SECRET_KEY:
            send_message(sender_number, "❌ Invalid passcode.")
            return

        send_message(sender_number, "✅ Roger that. Sending a test briefing to you now...")
        send_test_briefing(sender_number)
        return
        
    elif user_text.lower() == ".nuke":
        if not DEV_PHONE_NUMBER or sender_number != DEV_PHONE_NUMBER:
            send_message(sender_number, "❌ Unauthorized: This is a developer-only command.")
            return
        
        result = delete_all_users_from_db()
        count = result.deleted_count
        send_message(sender_number, f"💥 NUKE COMPLETE 💥\n\nSuccessfully deleted {count} user(s) from the database. The bot has been reset.")
        return

    elif user_text.lower() == ".stats":
        if not DEV_PHONE_NUMBER or sender_number != DEV_PHONE_NUMBER:
            send_message(sender_number, "❌ Unauthorized: This is a developer-only command.")
            return
        
        count = count_users_in_db()
        stats_message = f"📊 *Bot Statistics*\n\nTotal Registered Users: *{count}*"
        send_message(sender_number, stats_message)
        return

    if isinstance(state, dict) and state.get("state") == "awaiting_document_question":
        if not is_document_followup_question(user_text):
            user_sessions.pop(sender_number, None)
            state = None
        else:
            doc_type = state.get("doc_type")
            doc_text = state.get("document_text")
            doc_data = state.get("data", {})

            if doc_type == "meeting_invite" and user_text.lower() in ["yes", "ok", "sure", "yep", "schedule it"]:
                task = doc_data.get("task")
                timestamp = doc_data.get("timestamp")
                if task and timestamp:
                    response = schedule_reminder(f"Remind me about {task} at {timestamp}", sender_number, get_credentials_from_db, scheduler)
                    send_message(sender_number, response)
                else:
                    send_message(sender_number, "I seem to have lost the details. Could you try uploading the invite again?")
                user_sessions.pop(sender_number, None)
            else:
                send_message(sender_number, "🤖 Thinking...")
                response = get_contextual_ai_response(doc_text, user_text)
                send_message(sender_number, response)
                send_message(sender_number, "_You can ask another question, or type `menu` to exit._")
            return
    
    user_data = get_user_from_db(sender_number)

    if any(keyword in user_text_lower for keyword in ['excel', 'sheet', 'report', 'export']):
        send_message(sender_number, "📊 Generating your expense report...")
        file_path = export_expenses_to_excel(sender_number, user_data)
        if file_path:
            send_file_to_user(sender_number, file_path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Here is your expense report.xlsx")
            os.remove(file_path)
        else:
            send_message(sender_number, "You have no expenses to export yet.")
        return

    if is_expense_intent(user_text):
        send_message(sender_number, "Analyzing expense...")
        expenses = parse_expense_with_grok(user_text)
        if expenses:
            confirmations = [log_expense(sender_number, e.get('cost'), e.get('item'), e.get('place'), e.get('timestamp')) if isinstance(e.get('cost'), (int, float)) else f"❓ Could not log '{e.get('item')}' - cost is unclear." for e in expenses]
            send_message(sender_number, "\n".join(confirmations))
        else:
            send_message(sender_number, "Sorry, I couldn't understand that as an expense. Try being more specific about the cost and item.")
        return

    response_text = ""

    greetings = ["hi", "hello", "hey"]
    is_greeting = any(user_text_lower.startswith(greet) for greet in greetings)

    if state == "awaiting_name":
        name = user_text.split()[0].title()
        new_user_data = {"name": name, "expenses": [], "is_google_connected": False}
        create_or_update_user_in_db(sender_number, new_user_data)
        user_sessions.pop(sender_number, None)
        send_message(sender_number, f"✅ Got it! I’ll remember you as *{name}*.")
        time.sleep(1)

        if GOOGLE_REDIRECT_URI:
            try:
                parsed_uri = urlparse(request.url_root)
                base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                auth_link = f"{base_url}/google-auth?state={sender_number}"
                
                auth_message = (
                    "To get the most out of me (like email summaries and calendar events), connect your Google Account. "
                    f"Click here to connect: {auth_link}"
                )
                send_message(sender_number, auth_message)
                time.sleep(2)
            except Exception as e:
                print(f"Error generating Google Auth link: {e}")

        send_welcome_message(sender_number, name)
        return
    
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
            full_prompt = f"Write an email with the subject '{state['subject']}'. Use the following details:\n" + "\n".join([f"- {q}: {a}" for q, a in zip(state["questions"], state["answers"])])
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
    elif isinstance(state, dict) and state.get("state") == "awaiting_email_edit":
        if user_text_lower in ["send", "send it", "approve", "ok send", "yes send"]:
            send_message(sender_number, "✅ Okay, sending the email from your account...")
            
            creds = get_credentials_from_db(sender_number)
            if creds:
                attachment_paths = state.get("attachment_paths", [])
                response_text = send_email(creds, state["recipients"], state["subject"], state["body"], attachment_paths)
                for path in attachment_paths:
                    if os.path.exists(path): os.remove(path)
                user_sessions.pop(sender_number, None)
            else:
                response_text = "❌ Could not send email. Your Google account is not connected properly. Please try re-connecting."
            
        elif user_text_lower == "attach":
            state["state"] = "awaiting_email_attachment"
            user_sessions[sender_number] = state
            response_text = "📎 Please upload the first file you want to attach."
        else:
            _, timestamp_str = parse_reminder_with_grok(user_text)
            if timestamp_str:
                try:
                    tz = pytz.timezone('Asia/Kolkata')
                    now = datetime.now(tz)
                    run_time = date_parser.parse(timestamp_str)
                    if run_time.tzinfo is None:
                        run_time = tz.localize(run_time)
                    if run_time < now:
                        response_text = f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) is in the past."
                    else:
                        creds = get_credentials_from_db(sender_number)
                        if creds:
                            attachment_paths = state.get("attachment_paths", [])
                            scheduler.add_job(func=send_email, trigger='date', run_date=run_time, args=[creds, state["recipients"], state["subject"], state["body"], attachment_paths])
                            response_text = f"👍 Scheduled! The email will be sent from your account on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
                        else:
                            response_text = "❌ Could not schedule email. Your Google account is not connected."
                        user_sessions.pop(sender_number, None)
                except (date_parser.ParserError, ValueError) as e:
                    print(f"Error parsing timestamp from Grok: {e}")
                    response_text = "I understood you want to schedule the email, but had trouble with the exact time."
            else:
                send_message(sender_number, "✏️ Applying your changes, please wait...")
                new_body = edit_email_body(state["body"], user_text)
                if new_body:
                    user_sessions[sender_number]["body"] = new_body
                    response_text = f"Here is the updated draft:\n\n---\n{new_body}\n---\n\n_Ask for more changes, type *'attach'* for a file, or type *'send'*._"
                else:
                    response_text = "Sorry, I couldn't apply that change."
    elif state == "awaiting_reminder":
        response_text = schedule_reminder(user_text, sender_number, get_credentials_from_db, scheduler)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_grammar":
        response_text = correct_grammar_with_grok(user_text)
        user_sessions.pop(sender_number, None)
    elif state == "awaiting_ai":
        response_text = ai_reply(user_text)
    elif state == "awaiting_translation":
        response_text = translate_with_grok(user_text)
        user_sessions.pop(sender_number, None)
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
    
    elif is_greeting:
        user_sessions.pop(sender_number, None)
        if not user_data:
            response_text = "👋 Hi there! To personalize your experience, what should I call you?"
            user_sessions[sender_number] = "awaiting_name"
        else:
            send_welcome_message(sender_number, user_data.get("name"))
    
    else: # Main Menu selections or button replies
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
            send_conversion_menu(sender_number)
        elif user_text == "5":
            user_sessions[sender_number] = "awaiting_translation"
            response_text = "🌍 *AI Translator Active!*\n\nHow can I help you translate today?"
        elif user_text == "6":
            user_sessions[sender_number] = "awaiting_weather"
            response_text = "🏙️ Enter a city or location to get the current weather."
        elif user_text == "7":
            user_sessions[sender_number] = "awaiting_currency_conversion"
            response_text = "💱 *Currency Converter*\n\nAsk me to convert currencies naturally!"
        elif user_text == "8":
            creds = get_credentials_from_db(sender_number)
            if creds:
                user_sessions[sender_number] = "awaiting_email_recipient"
                response_text = "📧 *AI Email Assistant*\n\nWho are the recipients? (Emails separated by commas)"
            else:
                response_text = "⚠️ To use the AI Email Assistant, you must first connect your Google account. Please use the link I sent you during setup."
        
        elif user_text == "conv_pdf_to_text":
            user_sessions[sender_number] = "awaiting_pdf_to_text"
            response_text = "📥 Please upload the PDF you want to convert to text."
        elif user_text == "conv_text_to_pdf":
            user_sessions[sender_number] = "awaiting_text_to_pdf"
            response_text = "📝 Please send the text you want to convert into a PDF."
        elif user_text == "conv_pdf_to_word":
            user_sessions[sender_number] = "awaiting_pdf_to_docx"
            response_text = "📥 Please upload the PDF to convert into Word."
        elif user_text == "conv_text_to_word":
            user_sessions[sender_number] = "awaiting_text_to_word"
            response_text = "📝 Please send the text you want to convert into a Word document."
            
        elif not state:
            response_text = "🤔 I didn't understand that. Please type *menu* to see the options."

    if response_text:
        send_message(sender_number, response_text)


# === UI, HELPERS, & LOGIC FUNCTIONS ===
def send_welcome_message(to, name):
    send_interactive_menu(to, name)

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

def convert_text_to_pdf(text):
    pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text.encode('latin-1', 'replace').decode('latin-1'))
    filename = secure_filename(f"converted_{int(time.time())}.pdf")
    file_path = os.path.join("uploads", filename)
    pdf.output(file_path); return file_path

def convert_text_to_word(text):
    doc = Document(); doc.add_paragraph(text)
    filename = secure_filename(f"converted_{int(time.time())}.docx")
    file_path = os.path.join("uploads", filename)
    doc.save(file_path); return file_path

def log_expense(sender_number, amount, item, place=None, timestamp_str=None):
    user_data = get_user_from_db(sender_number)
    if not user_data:
        user_data = {"_id": sender_number, "name": "User", "expenses": [], "is_google_connected": False}

    try:
        expense_time = date_parser.parse(timestamp_str) if timestamp_str else datetime.now(pytz.timezone('Asia/Kolkata'))
    except (date_parser.ParserError, pytz.exceptions.AmbiguousTimeError):
        expense_time = datetime.now(pytz.timezone('Asia/Kolkata'))

    tz = pytz.timezone('Asia/Kolkata')
    if expense_time.tzinfo is None:
        expense_time = tz.localize(expense_time)

    new_expense = {"cost": amount, "item": item, "place": place or "N/A", "timestamp": expense_time.isoformat()}

    if "expenses" not in user_data:
        user_data["expenses"] = []
    user_data["expenses"].append(new_expense)

    create_or_update_user_in_db(sender_number, user_data)

    log_message = f"✅ Logged: *₹{amount:.2f}* for *{item.title()}*"
    if place and place != "N/A": log_message += f" at *{place.title()}*"
    if expense_time.date() != datetime.now(tz).date(): log_message += f" on *{expense_time.strftime('%B %d')}*"
    return log_message

def export_expenses_to_excel(sender_number, user_data):
    user_expenses = user_data.get("expenses", []) if user_data else []
    if not user_expenses: return None
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
    all_users = list(get_all_users_from_db())
    if not all_users:
        print("No users found. Skipping job.")
        return

    headline = get_tech_headline()
    weather = get_briefing_weather("Vijayawada")
    tech_tip = get_tech_tip()
    quote = get_daily_quote()

    print(f"Found {len(all_users)} user(s) to send briefing to.")
    for user in all_users:
        user_id = user["_id"]
        user_name = user.get("name", "there")

        email_summary = "Not connected."
        if user.get("is_google_connected"):
            creds = get_credentials_from_db(user_id)
            if creds:
                summary = get_email_summary(creds)
                if summary:
                    email_summary = summary
                else:
                    email_summary = "No important updates found."

        template_name = "daily_briefing"
        components = [
            {"type": "header", "parameters": [{"type": "text", "text": user_name}]},
            {"type": "body", "parameters": [
                {"type": "text", "text": quote},
                {"type": "text", "text": email_summary},
                {"type": "text", "text": headline},
                {"type": "text", "text": weather},
                {"type": "text", "text": tech_tip}
            ]}
        ]

        send_template_message(user_id, template_name, components)
        time.sleep(1)
    print("--- Daily Briefing Job Finished ---")

def send_test_briefing(developer_number):
    """Sends a test daily briefing only to the developer."""
    print(f"--- Running Test Briefing for {developer_number} ---")
    user = get_user_from_db(developer_number)
    if not user:
        send_message(developer_number, "Could not send test briefing. Your user profile was not found in the database.")
        return

    headline = get_tech_headline()
    weather = get_briefing_weather("Vijayawada")
    tech_tip = get_tech_tip()
    quote = get_daily_quote()

    user_name = user.get("name", "Developer")

    email_summary = "Not connected."
    if user.get("is_google_connected"):
        creds = get_credentials_from_db(developer_number)
        if creds:
            summary = get_email_summary(creds)
            if summary:
                email_summary = summary
            else:
                email_summary = "No important updates found."

    template_name = "daily_briefing"
    components = [
        {"type": "header", "parameters": [{"type": "text", "text": user_name}]},
        {"type": "body", "parameters": [
            {"type": "text", "text": quote},
            {"type": "text", "text": email_summary},
            {"type": "text", "text": headline},
            {"type": "text", "text": weather},
            {"type": "text", "text": tech_tip}
        ]}
    ]

    send_template_message(developer_number, template_name, components)
    print("--- Test Briefing Finished ---")


def send_update_notification_to_all_users(feature_list):
    if not ADMIN_SECRET_KEY:
        print("ADMIN_SECRET_KEY is not set. Cannot send notifications.")
        return
    print("--- Sending update notifications to all users ---")
    all_users = list(get_all_users_from_db())
    if not all_users:
        print("No users found, skipping notifications.")
        return

    template_name = "bot_update_notification"

    components = [{
        "type": "body",
        "parameters": [{
            "type": "text",
            "text": feature_list
        }]
    }]

    print(f"Found {len(all_users)} user(s). Preparing to send update templates...")
    for user in all_users:
        send_template_message(user["_id"], template_name, components)
        time.sleep(1)
    print("--- Finished sending update notifications ---")


# --- RUN APP ---
if __name__ == '__main__':
    if not scheduler.get_job('daily_briefing_job'):
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
