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
from apscheduler.jobstores.mongodb import MongoDBJobStore
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
    route_user_intent,
    generate_full_daily_briefing,
    ai_reply,
    correct_grammar_with_grok,
    analyze_email_subject,
    edit_email_body,
    write_email_body_with_grok,
    translate_with_grok,
    analyze_document_context,
    get_contextual_ai_response,
    is_document_followup_question
)
from email_sender import send_email
from services import get_daily_quote, get_on_this_day_in_history, get_raw_weather_data, get_indian_festival_today
from google_calendar_integration import get_google_auth_flow, create_google_calendar_event
from reminders import schedule_reminder, get_all_reminders, delete_reminder
from messaging import send_message, send_template_message, send_interactive_menu, send_conversion_menu, send_reminders_list, send_delete_confirmation, send_google_drive_menu
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


# --- DATABASE & SCHEDULER ---
client = MongoClient(MONGO_URI)
db = client.ai_buddy_db
users_collection = db.users
jobs_collection = db.scheduled_jobs

jobstores = {
    'default': MongoDBJobStore(client=client, database="ai_buddy_db", collection="scheduled_jobs")
}
scheduler = BackgroundScheduler(jobstores=jobstores, timezone=pytz.timezone('Asia/Kolkata'))
scheduler.start()


if not os.path.exists("uploads"):
    os.makedirs("uploads")

# === HELPER FUNCTIONS ===
def get_user_from_db(sender_number):
    return users_collection.find_one({"_id": sender_number})

def create_or_update_user_in_db(sender_number, data):
    users_collection.update_one({"_id": sender_number}, {"$set": data}, upsert=True)

def set_user_session(sender_number, session_data):
    if session_data is None:
        users_collection.update_one({"_id": sender_number}, {"$unset": {"session": ""}})
    else:
        users_collection.update_one({"_id": sender_number}, {"$set": {"session": session_data}}, upsert=True)

def get_user_session(sender_number):
    user_data = get_user_from_db(sender_number)
    return user_data.get("session") if user_data else None

def get_all_users_from_db():
    return users_collection.find({}, {"_id": 1, "name": 1, "is_google_connected": 1, "location": 1})

def delete_all_users_from_db():
    return users_collection.delete_many({})

def delete_all_scheduled_jobs_from_db():
    """Deletes all scheduled jobs from the database."""
    return jobs_collection.delete_many({})

def count_users_in_db():
    return users_collection.count_documents({})

def save_credentials_to_db(sender_number, credentials):
    pickled_creds = pickle.dumps(credentials)
    create_or_update_user_in_db(sender_number, {"google_credentials": pickled_creds, "is_google_connected": True})

def get_credentials_from_db(sender_number):
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

def send_google_auth_link(sender_number):
    """Generates and sends the Google authentication link to a user."""
    if GOOGLE_REDIRECT_URI:
        try:
            base_url = request.url_root
            auth_link = f"{base_url}google-auth?state={sender_number}"
            auth_message = (
                "To connect or re-connect your Google Account for features like calendar events and email, "
                f"please click this link:\n\n{auth_link}"
            )
            send_message(sender_number, auth_message)
        except Exception as e:
            print(f"Error generating Google Auth link: {e}")
            send_message(sender_number, "Sorry, I couldn't generate a connection link right now.")
    else:
        send_message(sender_number, "Google connection is not configured on the server.")

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
    set_user_session(sender_number, None)
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

def download_media_from_whatsapp(media_id, message_type):
    try:
        url = f"https://graph.facebook.com/v19.0/{media_id}/"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        media_info = response.json()
        media_url = media_info['url']

        original_filename = f"media_{media_id}"
        if message_type == 'document' and 'document' in media_info:
            original_filename = media_info.get('document', {}).get('filename', original_filename)

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
        session_data = get_user_session(sender_number)
        msg_type = message.get("type")

        if msg_type == "interactive":
            interactive_data = message["interactive"]
            selection_id = ""
            if interactive_data["type"] == "list_reply":
                selection_id = interactive_data["list_reply"]["id"]
            elif interactive_data["type"] == "button_reply":
                selection_id = interactive_data["button_reply"]["id"]
            
            if selection_id:
                handle_text_message(selection_id, sender_number, session_data)
        elif msg_type == "text":
            user_text = message["text"]["body"].strip()
            handle_text_message(user_text, sender_number, session_data)
        elif msg_type in ["document", "image"]:
            handle_document_message(message, sender_number, session_data, msg_type)
        else:
            send_message(sender_number, "🤔 Sorry, I can only process text, documents, and images at the moment.")

    except Exception as e:
        print(f"❌ Unhandled Error: {e}")
    return "OK", 200

# === MESSAGE HANDLERS ===
def handle_document_message(message, sender_number, session_data, message_type):
    media_id = message.get(message_type, {}).get('id')
    if not media_id:
        send_message(sender_number, "❌ I couldn't find the file in your message.")
        return

    downloaded_path = None
    try:
        if isinstance(session_data, dict) and session_data.get("state") == "awaiting_email_attachment":
            filename = message.get('document', {}).get('filename', 'attached_file')
            send_message(sender_number, f"Got it. Attaching `{filename}` to your email...")
            downloaded_path, _ = download_media_from_whatsapp(media_id, message_type)
            if downloaded_path:
                if "attachment_paths" not in session_data:
                    session_data["attachment_paths"] = []
                session_data["attachment_paths"].append(downloaded_path)
                session_data["state"] = "awaiting_more_attachments"
                set_user_session(sender_number, session_data)
                response_text = f"✅ File attached successfully!\n\nType *'done'* when you have finished attaching files, or upload another document."
                send_message(sender_number, response_text)
            else:
                send_message(sender_number, "❌ Sorry, I couldn't download your attachment. Please try again.")
            return

        simple_state = session_data if isinstance(session_data, str) else None

        if simple_state in ["awaiting_pdf_to_text", "awaiting_pdf_to_docx"]:
            downloaded_path, mime_type = download_media_from_whatsapp(media_id, message_type)
            if not downloaded_path:
                send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
                return
            
            if simple_state == "awaiting_pdf_to_text":
                extracted_text = get_text_from_file(downloaded_path, mime_type)
                response = extracted_text if extracted_text else "Could not find any readable text in the PDF."
                send_message(sender_number, response)
            elif simple_state == "awaiting_pdf_to_docx":
                output_docx_path = downloaded_path + ".docx"
                cv = Converter(downloaded_path)
                cv.convert(output_docx_path, start=0, end=None)
                cv.close()
                send_file_to_user(sender_number, output_docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
                if os.path.exists(output_docx_path): os.remove(output_docx_path)
            set_user_session(sender_number, None)
            return

        send_message(sender_number, "📄 Got your file! Analyzing it with AI...")
        downloaded_path, mime_type = download_media_from_whatsapp(media_id, message_type)
        if not downloaded_path:
            send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
            return
            
        extracted_text = get_text_from_file(downloaded_path, mime_type)
        if not extracted_text:
            send_message(sender_number, "❌ I couldn't find any readable text in that file.")
            return

        analysis = analyze_document_context(extracted_text)
        if not analysis:
            send_message(sender_number, "🤔 I analyzed the document, but I'm not sure what to do with it.")
            set_user_session(sender_number, None)
            return
            
        doc_type = analysis.get("doc_type")
        data = analysis.get("data", {})

        new_session = {"state": "awaiting_document_question", "document_text": extracted_text, "doc_type": doc_type, "data": data}
        set_user_session(sender_number, new_session)

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
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            os.remove(downloaded_path)

def handle_text_message(user_text, sender_number, session_data):
    user_text_lower = user_text.lower()
    menu_commands = ["start", "menu", "help", "options", "0"]
    greetings = ["hi", "hello", "hey"]
    
    if user_text.startswith("delete_reminder_"):
        job_id_to_delete = user_text.split("delete_reminder_")[1]
        reminders = get_all_reminders(sender_number, scheduler)
        task_to_delete = next((rem['task'] for rem in reminders if rem['id'] == job_id_to_delete), "this reminder")
        send_delete_confirmation(sender_number, job_id_to_delete, task_to_delete)
        return

    if user_text.startswith("confirm_delete_"):
        job_id_to_delete = user_text.split("confirm_delete_")[1]
        if delete_reminder(job_id_to_delete, scheduler):
            send_message(sender_number, "✅ Reminder successfully deleted.")
        else:
            send_message(sender_number, "❌ Could not delete the reminder. It might have already been removed.")
        return
    
    if user_text == "cancel_delete":
        send_message(sender_number, "Deletion cancelled.")
        return

    if user_text.startswith("."):
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
            
            user_result = delete_all_users_from_db()
            scheduler.remove_all_jobs()
            user_count = user_result.deleted_count
            send_message(sender_number, f"💥 NUKE COMPLETE 💥\n\nSuccessfully deleted {user_count} user(s) and all scheduled reminders. The bot has been reset.")
            return

        elif user_text.lower() == ".stats":
            if not DEV_PHONE_NUMBER or sender_number != DEV_PHONE_NUMBER:
                send_message(sender_number, "❌ Unauthorized: This is a developer-only command.")
                return
            count = count_users_in_db()
            stats_message = f"📊 *Bot Statistics*\n\nTotal Registered Users: *{count}*"
            send_message(sender_number, stats_message)
            return
        
        elif user_text.lower() == ".reconnect":
            send_google_auth_link(sender_number)
            return
        
        elif user_text.lower() == ".reminders":
            reminders = get_all_reminders(sender_number, scheduler)
            send_reminders_list(sender_number, reminders)
            return

    current_state = None
    if isinstance(session_data, dict):
        current_state = session_data.get("state")
    elif isinstance(session_data, str):
        current_state = session_data

    if current_state:
        if current_state == "awaiting_reminder_text":
            send_message(sender_number, "Got it! I'm working on scheduling your reminders. This might take a moment...")
            scheduler.add_job(
                func=process_and_schedule_reminders,
                trigger='date',
                run_date=datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(seconds=2),
                args=[user_text, sender_number]
            )
            set_user_session(sender_number, None)
            return

        if current_state == "awaiting_document_question":
            if not is_document_followup_question(user_text):
                set_user_session(sender_number, None)
            else:
                doc_text = session_data.get("document_text")
                send_message(sender_number, "🤖 Thinking...")
                response = get_contextual_ai_response(doc_text, user_text)
                send_message(sender_number, response)
                send_message(sender_number, "_You can ask another question, or type `menu` to exit._")
                return

        if current_state == "awaiting_grammar":
            response_text = correct_grammar_with_grok(user_text)
            set_user_session(sender_number, None)
            send_message(sender_number, response_text)
            return
        elif current_state == "awaiting_ai":
            if user_text_lower in menu_commands or any(greet in user_text_lower for greet in greetings):
                set_user_session(sender_number, None)
                user_data = get_user_from_db(sender_number)
                send_welcome_message(sender_number, user_data.get("name", "User"))
            else:
                response_text = ai_reply(user_text)
                send_message(sender_number, response_text)
            return
        elif current_state == "awaiting_translation":
            response_text = translate_with_grok(user_text)
            set_user_session(sender_number, None)
            send_message(sender_number, response_text)
            return
        elif current_state == "awaiting_text_to_pdf":
            pdf_path = convert_text_to_pdf(user_text)
            send_file_to_user(sender_number, pdf_path, "application/pdf", "📄 Here is your converted PDF file.")
            if os.path.exists(pdf_path): os.remove(pdf_path)
            set_user_session(sender_number, None)
            return
        elif current_state == "awaiting_text_to_word":
            docx_path = convert_text_to_word(user_text)
            send_file_to_user(sender_number, docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
            if os.path.exists(docx_path): os.remove(docx_path)
            set_user_session(sender_number, None)
            return
        elif current_state == "awaiting_name":
            name = user_text.split()[0].title()
            create_or_update_user_in_db(sender_number, {"name": name, "expenses": [], "is_google_connected": False, "location": None})
            set_user_session(sender_number, "awaiting_location")
            send_message(sender_number, f"✅ Got it! I’ll remember you as *{name}*.")
            time.sleep(1)
            send_message(sender_number, "To provide you with accurate weather in your morning briefings, what city do you live in?")
            return
        
        elif current_state == "awaiting_location":
            create_or_update_user_in_db(sender_number, {"location": user_text.title()})
            set_user_session(sender_number, None)
            send_message(sender_number, f"✅ Great! I've set your location to *{user_text.title()}*.")
            time.sleep(1)
            send_google_auth_link(sender_number)
            time.sleep(2)
            send_welcome_message(sender_number, get_user_from_db(sender_number).get("name"))
            return
        
        elif current_state == "awaiting_weather":
            response_text = get_weather(user_text)
            set_user_session(sender_number, None)
            send_message(sender_number, response_text)
            return

        if current_state == "awaiting_email_recipient":
            recipients = [email.strip() for email in user_text.split(',')]
            valid_recipients = [email for email in recipients if re.match(r"[^@]+@[^@]+\.[^@]+", email)]
            if valid_recipients:
                new_session = {"state": "awaiting_email_subject", "recipients": valid_recipients}
                set_user_session(sender_number, new_session)
                send_message(sender_number, f"✅ Got recipient(s). Now, what should the subject of the email be?")
            else:
                send_message(sender_number, "⚠️ I couldn't find any valid email addresses. Please try again.")
            return
        
        elif current_state == "awaiting_email_subject":
            subject = user_text
            send_message(sender_number, "👍 Great subject. Let me think of some follow-up questions...")
            questions = analyze_email_subject(subject)
            session_data["subject"] = subject
            if questions:
                session_data["state"] = "gathering_email_details"
                session_data["questions"] = questions
                session_data["answers"] = []
                session_data["current_question_index"] = 0
                send_message(sender_number, questions[0])
            else:
                session_data["state"] = "awaiting_email_prompt_fallback"
                send_message(sender_number, "Okay, I'll just need one main prompt. What should the email be about?")
            set_user_session(sender_number, session_data)
            return
            
        elif current_state == "gathering_email_details":
            session_data["answers"].append(user_text)
            session_data["current_question_index"] += 1
            if session_data["current_question_index"] < len(session_data["questions"]):
                send_message(sender_number, session_data["questions"][session_data["current_question_index"]])
                set_user_session(sender_number, session_data)
            else:
                send_message(sender_number, "🤖 Got all the details. Writing your email with AI, please wait...")
                full_prompt = f"Write an email with the subject '{session_data['subject']}'. Use the following details:\n" + "\n".join([f"- {q}: {a}" for q, a in zip(session_data["questions"], session_data["answers"])])
                email_body = write_email_body_with_grok(full_prompt)
                if "❌" in email_body:
                    send_message(sender_number, email_body)
                    set_user_session(sender_number, None)
                else:
                    session_data["state"] = "awaiting_email_edit"
                    session_data["body"] = email_body
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, f"Here is the draft:\n\n---\n{email_body}\n---\n\n_You can ask for changes, type *'attach'* to add a file, or type *'send'* to approve._")
            return

        elif current_state == "awaiting_email_prompt_fallback":
            prompt = user_text
            send_message(sender_number, "🤖 Writing your email with AI, please wait...")
            email_body = write_email_body_with_grok(prompt)
            if "❌" in email_body:
                send_message(sender_number, email_body)
                set_user_session(sender_number, None)
            else:
                session_data["state"] = "awaiting_email_edit"
                session_data["body"] = email_body
                set_user_session(sender_number, session_data)
                send_message(sender_number, f"Here is the draft:\n\n---\n{email_body}\n---\n\n_You can ask for changes, type *'attach'* to add a file, or type *'send'* to approve._")
            return
                
        elif current_state == "awaiting_more_attachments":
            if user_text_lower == "done":
                session_data["state"] = "awaiting_email_edit"
                set_user_session(sender_number, session_data)
                num_files = len(session_data.get("attachment_paths", []))
                send_message(sender_number, f"✅ Okay, {num_files} file(s) are attached. You can now review the draft, ask for more changes, or type *'send'*.")
            else:
                send_message(sender_number, "Please upload another file, or type *'done'* to finish.")
            return
                
        elif current_state == "awaiting_email_edit":
            if user_text_lower in ["send", "send it", "approve", "ok send", "yes send"]:
                send_message(sender_number, "✅ Okay, sending the email from your account...")
                creds = get_credentials_from_db(sender_number)
                if creds:
                    attachment_paths = session_data.get("attachment_paths", [])
                    response_text = send_email(creds, session_data["recipients"], session_data["subject"], session_data["body"], attachment_paths)
                    for path in attachment_paths:
                        if os.path.exists(path): os.remove(path)
                    send_message(sender_number, response_text)
                else:
                    send_message(sender_number, "❌ Could not send email. Your Google account is not connected properly. Please try re-connecting.")
                set_user_session(sender_number, None)
            elif user_text_lower == "attach":
                session_data["state"] = "awaiting_email_attachment"
                set_user_session(sender_number, session_data)
                send_message(sender_number, "📎 Please upload the first file you want to attach.")
            else:
                send_message(sender_number, "✏️ Applying your changes, please wait...")
                new_body = edit_email_body(session_data["body"], user_text)
                if new_body:
                    session_data["body"] = new_body
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, f"Here is the updated draft:\n\n---\n{new_body}\n---\n\n_Ask for more changes, type *'attach'* for a file, or type *'send'*._")
                else:
                    send_message(sender_number, "Sorry, I couldn't apply that change.")
            return
        
    if user_text_lower in menu_commands or any(greet in user_text_lower for greet in greetings):
        set_user_session(sender_number, None)
        user_data = get_user_from_db(sender_number)
        if not user_data:
            set_user_session(sender_number, "awaiting_name")
            send_message(sender_number, "👋 Hi there! To personalize your experience, what should I call you?")
        else:
            send_welcome_message(sender_number, user_data.get("name"))
        return

    if user_text == "1":
        set_user_session(sender_number, "awaiting_reminder_text")
        send_message(sender_number, "🕒 Sure, what's the reminder? (e.g., 'Call mom tomorrow at 5pm')")
        return
    elif user_text == "2":
        set_user_session(sender_number, "awaiting_grammar")
        send_message(sender_number, "✍️ Send me the sentence or paragraph you want me to correct.")
        return
    elif user_text == "3":
        set_user_session(sender_number, "awaiting_ai")
        send_message(sender_number, "🤖 I'm ready! Ask me anything, and I'll do my best to answer.")
        return
    elif user_text == "4":
        send_conversion_menu(sender_number)
        return
    elif user_text == "5":
        set_user_session(sender_number, "awaiting_translation")
        send_message(sender_number, "🌍 What text would you like to translate, and to which language? (e.g., 'Hello how are you to Spanish')")
        return
    elif user_text == "6":
        set_user_session(sender_number, "awaiting_weather")
        send_message(sender_number, "🏙️ Enter a city or location to get the current weather.")
        return
    elif user_text == "7":
        send_message(sender_number, "💱 What would you like to convert? (e.g., '100 USD to INR')")
        return
    elif user_text == "8":
        creds = get_credentials_from_db(sender_number)
        if creds:
            set_user_session(sender_number, "awaiting_email_recipient")
            send_message(sender_number, "📧 *AI Email Assistant*\n\nWho are the recipients? (Emails separated by commas)")
        else:
            send_message(sender_number, "⚠️ To use the AI Email Assistant, you must first connect your Google account.")
        return
    elif user_text == "9":
        creds = get_credentials_from_db(sender_number)
        if creds:
            send_google_drive_menu(sender_number)
        else:
            send_message(sender_number, "⚠️ To use Google Drive features, you must first connect your Google account.")
        return
    elif user_text == "reminders_check":
        reminders = get_all_reminders(sender_number, scheduler)
        send_reminders_list(sender_number, reminders)
        return
    elif user_text == "conv_pdf_to_text":
        set_user_session(sender_number, "awaiting_pdf_to_text")
        send_message(sender_number, "📄 Please send the PDF file you want to convert to text.")
        return
    elif user_text == "conv_text_to_pdf":
        set_user_session(sender_number, "awaiting_text_to_pdf")
        send_message(sender_number, "📝 Please send the text you want to convert into a PDF document.")
        return
    elif user_text == "conv_pdf_to_word":
        set_user_session(sender_number, "awaiting_pdf_to_docx")
        send_message(sender_number, "📄 Please send the PDF file you want to convert to a Word document.")
        return
    elif user_text == "conv_text_to_word":
        set_user_session(sender_number, "awaiting_text_to_word")
        send_message(sender_number, "📝 Please send the text you want to convert into a Word document.")
        return

    send_message(sender_number, "🤖 Analyzing...")
    scheduler.add_job(
        func=process_natural_language_request,
        trigger='date',
        run_date=datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(seconds=1),
        args=[user_text, sender_number]
    )


# === UI, HELPERS, & LOGIC FUNCTIONS ===
def process_natural_language_request(user_text, sender_number):
    intent_data = route_user_intent(user_text)
    intent = intent_data.get("intent")
    entities = intent_data.get("entities")
    response_text = ""

    if intent == "set_reminder":
        reminders_to_set = entities
        if isinstance(reminders_to_set, list) and reminders_to_set:
            if len(reminders_to_set) > 1:
                send_message(sender_number, f"Got it! Scheduling {len(reminders_to_set)} reminders for you. I'll send a confirmation for each one.")
            for rem in reminders_to_set:
                 task = rem.get("task")
                 timestamp = rem.get("timestamp")
                 recurrence = rem.get("recurrence")
                 conf = schedule_reminder(task, timestamp, recurrence, sender_number, get_credentials_from_db, scheduler)
                 send_message(sender_number, conf)
                 time.sleep(1)
            return
        else:
            response_text = "Sorry, I couldn't find any reminders to set in your message."

    elif intent == "log_expense":
        if entities:
            confirmations = [log_expense(sender_number, e.get('cost'), e.get('item'), e.get('place'), e.get('timestamp')) for e in entities if isinstance(e.get('cost'), (int, float))]
            response_text = "\n".join(confirmations)
        else:
            response_text = "Sorry, I couldn't understand that as an expense."

    elif intent == "export_expenses":
        send_message(sender_number, "📊 Generating your expense report...")
        user_data = get_user_from_db(sender_number)
        file_path = export_expenses_to_excel(sender_number, user_data)
        if file_path:
            send_file_to_user(sender_number, file_path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Here is your expense report.")
            os.remove(file_path)
        else:
            send_message(sender_number, "You have no expenses to export yet.")
        return 

    elif intent == "get_reminders":
        reminders = get_all_reminders(sender_number, scheduler)
        send_reminders_list(sender_number, reminders)
        return

    elif intent == "convert_currency":
        if entities:
            results = [convert_currency(c.get('amount'), c.get('from_currency'), c.get('to_currency')) for c in entities]
            response_text = "\n\n".join(results)
        else:
            response_text = "Sorry, I couldn't understand that currency conversion."
    
    elif intent == "get_weather":
        location = entities.get("location", "Vijayawada")
        response_text = get_weather(location)
        
    elif intent == "general_query":
        response_text = ai_reply(user_text)

    else:
        response_text = "🤔 I'm not sure how to handle that. Please try rephrasing, or type *menu*."

    if response_text:
        send_message(sender_number, response_text)

def process_and_schedule_reminders(user_text, sender_number):
    intent_data = route_user_intent(user_text)
    if intent_data.get("intent") == "set_reminder":
        reminders_to_set = intent_data.get("entities", [])
        
        if isinstance(reminders_to_set, list) and reminders_to_set:
            if len(reminders_to_set) > 1:
                send_message(sender_number, f"Okay, scheduling {len(reminders_to_set)} reminders. I'll send a confirmation for each.")
            for rem in reminders_to_set:
                task = rem.get("task")
                timestamp = rem.get("timestamp")
                recurrence = rem.get("recurrence")
                conf = schedule_reminder(task, timestamp, recurrence, sender_number, get_credentials_from_db, scheduler)
                send_message(sender_number, conf)
                time.sleep(1)
        else:
            send_message(sender_number, "I couldn't find any reminders to set in that message.")
    else:
        send_message(sender_number, "I didn't understand that as a reminder. Please try again.")

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
        create_or_update_user_in_db(sender_number, {"name": "User", "expenses": [], "is_google_connected": False})

    try:
        expense_time = date_parser.parse(timestamp_str) if timestamp_str else datetime.now(pytz.timezone('Asia/Kolkata'))
    except (date_parser.ParserError, pytz.exceptions.AmbiguousTimeError):
        expense_time = datetime.now(pytz.timezone('Asia/Kolkata'))

    tz = pytz.timezone('Asia/Kolkata')
    if expense_time.tzinfo is None:
        expense_time = tz.localize(expense_time)

    new_expense = {"cost": amount, "item": item, "place": place or "N/A", "timestamp": expense_time.isoformat()}
    
    users_collection.update_one(
        {"_id": sender_number},
        {"$push": {"expenses": new_expense}},
        upsert=True
    )

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

    festival = get_indian_festival_today()
    quote, author = get_daily_quote()
    history_events = get_on_this_day_in_history()
    
    print(f"Found {len(all_users)} user(s) to send briefing to.")
    for user in all_users:
        user_id = user["_id"]
        user_name = user.get("name", "there")
        user_location = user.get("location", "Vijayawada") 
        weather_data = get_raw_weather_data(city=user_location)
        
        briefing_content = generate_full_daily_briefing(user_name, festival, quote, author, history_events, weather_data)
        
        greeting = briefing_content.get("greeting", f"☀️ Good Morning, {user_name}!")
        quote_explanation = briefing_content.get("quote_explanation", "Have a wonderful day!")
        detailed_history = briefing_content.get("detailed_history", "No historical fact found for today.")
        detailed_weather = briefing_content.get("detailed_weather", "Weather data is currently unavailable.")
        
        quote_explanation = quote_explanation.replace('\n', ' ')
        detailed_history = detailed_history.replace('\n', ' ')
        detailed_weather = detailed_weather.replace('\n', ' ')

        template_name = "daily_briefing_v3" 
        components = [
            {"type": "header", "parameters": [{"type": "text", "text": greeting}]},
            {"type": "body", "parameters": [
                {"type": "text", "text": f"{quote} - {author}"},
                {"type": "text", "text": quote_explanation},
                {"type": "text", "text": detailed_history},
                {"type": "text", "text": detailed_weather}
            ]}
        ]
        
        send_template_message(user_id, template_name, components)
        time.sleep(1)
    print("--- Daily Briefing Job Finished ---")

def send_test_briefing(developer_number):
    print(f"--- Running Test Briefing for {developer_number} ---")
    user = get_user_from_db(developer_number)
    if not user:
        send_message(developer_number, "Could not send test briefing. Your user profile was not found in the database.")
        return

    festival = get_indian_festival_today()
    quote, author = get_daily_quote()
    history_events = get_on_this_day_in_history()
    user_name = user.get("name", "Developer")
    user_location = user.get("location", "Vijayawada")
    weather_data = get_raw_weather_data(city=user_location)

    briefing_content = generate_full_daily_briefing(user_name, festival, quote, author, history_events, weather_data)
    
    greeting = briefing_content.get("greeting", f"☀️ Good Morning, {user_name}!")
    quote_explanation = briefing_content.get("quote_explanation", "Test explanation.")
    detailed_history = briefing_content.get("detailed_history", "Test history.")
    detailed_weather = briefing_content.get("detailed_weather", "Test weather.")

    quote_explanation = quote_explanation.replace('\n', ' ')
    detailed_history = detailed_history.replace('\n', ' ')
    detailed_weather = detailed_weather.replace('\n', ' ')

    template_name = "daily_briefing_v3"
    components = [
        {"type": "header", "parameters": [{"type": "text", "text": greeting}]},
        {"type": "body", "parameters": [
            {"type": "text", "text": f"{quote} - {author}"},
            {"type": "text", "text": quote_explanation},
            {"type": "text", "text": detailed_history},
            {"type": "text", "text": detailed_weather}
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


# === RUN APP ===
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
