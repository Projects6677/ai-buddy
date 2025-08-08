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
    get_chat_response,
    correct_grammar_with_grok,
    analyze_email_subject,
    edit_email_body,
    write_email_body_with_grok,
    analyze_document_context,
    is_document_followup_question,
    get_smart_greeting,
    get_conversational_weather
)
from email_sender import send_email
from services import get_daily_quote, get_on_this_day_in_history
from google_calendar_integration import get_google_auth_flow, create_google_calendar_event
from reminders import schedule_reminder, reminder_job
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


# --- DATABASE & SCHEDULER ---
client = MongoClient(MONGO_URI)
db = client.ai_buddy_db
users_collection = db.users

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
    return users_collection.find({}, {"_id": 1, "name": 1, "is_google_connected": 1})

def delete_all_users_from_db():
    return users_collection.delete_many({})

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

def send_message_to_all_users(message):
    """Sends a standard text message to all users in the database."""
    print(f"--- Sending message to all users: '{message}' ---")
    all_users = list(get_all_users_from_db())
    if not all_users:
        print("No users found. Skipping message.")
        return
    for user in all_users:
        user_id = user["_id"]
        send_message(user_id, message)
        time.sleep(1)
    print("Message sent to all users.")

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
        session_data = get_user_session(sender_number)
        msg_type = message.get("type")

        if msg_type == "interactive":
            selection_id = message["interactive"]["list_reply"]["id"] if "list_reply" in message["interactive"] else message["interactive"]["button_reply"]["id"]
            handle_text_message(selection_id, sender_number, session_data)
        elif msg_type == "text":
            user_text = message["text"]["body"].strip()
            handle_text_message(user_text, sender_number, session_data)
        elif msg_type in ["document", "image"]:
            handle_document_message(message, sender_number, session_data)
        else:
            send_message(sender_number, "🤔 Sorry, I can only process text, documents, and images at the moment.")

    except Exception as e:
        print(f"❌ Unhandled Error: {e}")
    return "OK", 200

# === MESSAGE HANDLERS ===
def handle_document_message(message, sender_number, session_data):
    media_id = message.get(message['type'], {}).get('id')
    if not media_id:
        send_message(sender_number, "❌ I couldn't find the file in your message.")
        return

    downloaded_path = None
    try:
        simple_state = session_data.get("state") if isinstance(session_data, dict) else session_data
        
        if simple_state == "awaiting_email_attachment" or simple_state == "awaiting_more_attachments":
            filename = message.get('document', {}).get('filename', 'attached_file')
            send_message(sender_number, f"Got it. Attaching `{filename}` to your email...")
            downloaded_path, _ = download_media_from_whatsapp(media_id)
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
        
        if simple_state == "awaiting_ai":
            send_message(sender_number, "📄 Got your file! Reading document into memory...")
            downloaded_path, mime_type = download_media_from_whatsapp(media_id)
            if not downloaded_path:
                send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
                return
            
            extracted_text = get_text_from_file(downloaded_path, mime_type)
            if not extracted_text:
                send_message(sender_number, "❌ I couldn't find any readable text in that file.")
                return
            
            new_session_data = {
                "state": "awaiting_ai",
                "document_text": extracted_text,
                "chat_history": [{"role": "system", "content": f"The user has uploaded a document with the following content: \n\n--- DOCUMENT START ---\n{extracted_text}\n--- END CONTEXT ---\n\nAnswer all subsequent questions based on the provided document. If you cannot find the answer in the document, say 'I couldn't find that information in the document.' Do not use any outside knowledge."}]
            }
            set_user_session(sender_number, new_session_data)
            
            send_message(sender_number, "✅ Document loaded! You can now ask me questions about it. \n\n_Type `menu` to clear the document and exit this mode._")
            return

        if simple_state == "awaiting_pdf_to_text":
            downloaded_path, mime_type = download_media_from_whatsapp(media_id)
            if not downloaded_path:
                send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
                return

            send_message(sender_number, "🔄 Extracting text from your PDF...")
            try:
                extracted_text = get_text_from_file(downloaded_path, mime_type)
                response = extracted_text if extracted_text else "❌ Could not find any readable text in the PDF."
                send_message(sender_number, response)
            except Exception as e:
                print(f"❌ PDF to Text conversion error: {e}")
                send_message(sender_number, "❌ Sorry, the PDF to text conversion failed. The file may be corrupted or in an unsupported format.")
            finally:
                if os.path.exists(downloaded_path): os.remove(downloaded_path)
            set_user_session(sender_number, None)
            return

        if simple_state == "awaiting_pdf_to_docx":
            downloaded_path, mime_type = download_media_from_whatsapp(media_id)
            if not downloaded_path:
                send_message(sender_number, "❌ Sorry, I couldn't download your file. Please try again.")
                return

            if not mime_type or not mime_type.startswith('application/pdf'):
                send_message(sender_number, "❌ I can only convert PDF files to Word. Please upload a PDF.")
                if os.path.exists(downloaded_path): os.remove(downloaded_path)
                return

            send_message(sender_number, "🔄 Converting your PDF to a Word document...")
            output_docx_path = downloaded_path + ".docx"
            set_user_session(sender_number, None)
            try:
                cv = Converter(downloaded_path)
                cv.convert(output_docx_path, start=0, end=None)
                cv.close()
                send_file_to_user(sender_number, output_docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 Here is your converted Word file.")
            except ValueError as e:
                print(f"❌ PDF to Word conversion error: {e}")
                send_message(sender_number, "❌ Sorry, the PDF to Word conversion failed. The file may be corrupted, encrypted, or in an unsupported format.")
            except Exception as e:
                print(f"❌ PDF to Word conversion error: {e}")
                send_message(sender_number, "❌ An unexpected error occurred during the PDF to Word conversion. Please try a different file.")
            finally:
                if os.path.exists(downloaded_path): os.remove(downloaded_path)
                if os.path.exists(output_docx_path): os.remove(output_docx_path)
            return
        
        send_message(sender_number, "🤔 I received a document, but I'm not in a mode to process it right now. Please select an option from the menu first.")
        
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            os.remove(downloaded_path)

def handle_text_message(user_text, sender_number, session_data):
    user_text_lower = user_text.lower()
    menu_commands = ["start", "menu", "help", "options", "0"]
    greetings = ["hi", "hello", "hey"]
    
    current_state = session_data.get("state") if isinstance(session_data, dict) else session_data

    user_data = get_user_from_db(sender_number)
    
    # --- FIX START ---
    # This block is now at the very beginning to prioritize new user onboarding.
    if not user_data and user_text_lower not in menu_commands and user_text_lower not in greetings and not current_state:
        set_user_session(sender_number, "awaiting_name")
        send_message(sender_number, "👋 Hi there! To personalize your experience, what should I call you?")
        return
    # --- FIX END ---
    
    if user_text_lower in menu_commands:
        set_user_session(sender_number, None)
        user_data = get_user_from_db(sender_number)
        send_welcome_message(sender_number, user_data.get("name", "User"))
        return
    elif user_text_lower == ".nuke":
        set_user_session(sender_number, "awaiting_nuke_confirmation")
        send_message(sender_number, "⚠️ WARNING! This will delete all user data from the database. Are you absolutely sure? Reply with `yes` to confirm.")
        return
    elif user_text_lower == ".stats":
        user_count = count_users_in_db()
        send_message(sender_number, f"📊 There are currently *{user_count}* users in the database.")
        return
    elif user_text_lower.startswith(".dev"):
        message_to_send = user_text.strip()[4:].strip()
        if message_to_send:
            send_message_to_all_users(message_to_send)
            send_message(sender_number, "✅ Message scheduled to be sent to all users.")
        else:
            send_message(sender_number, "Please provide a message after '.dev'. Usage: `.dev Your message here`")
        return
    elif user_text_lower == ".test":
        send_message(sender_number, "🛠 Sending you a test briefing now...")
        send_test_briefing(sender_number)
        return
    
    if user_text_lower in greetings:
        user_data = get_user_from_db(sender_number)
        if not user_data:
            set_user_session(sender_number, "awaiting_name")
            send_message(sender_number, "👋 Hi there! To personalize your experience, what should I call you?")
            return
        else:
            send_welcome_message(sender_number, user_data.get("name"))
        return

    if current_state:
        if current_state in ["awaiting_pdf_to_docx", "awaiting_pdf_to_text", "awaiting_text_to_pdf", "awaiting_text_to_word"]:
            send_message(sender_number, "Please upload a file or send text, depending on the conversion you selected.")
            return

        if current_state == "awaiting_nuke_confirmation":
            if user_text_lower == "yes":
                delete_all_users_from_db()
                send_message(sender_number, "💀 All user data has been permanently deleted.")
            else:
                send_message(sender_number, "👍 Deletion cancelled. All data is safe.")
            set_user_session(sender_number, None)
            return

        if current_state == "awaiting_reminder_text":
            send_message(sender_number, "🤖 Processing your reminder...")
            intent_data = route_user_intent(user_text)
            intent = intent_data.get("intent")
            entities = intent_data.get("entities")
            response_text = ""
            if intent == "set_reminder":
                task = entities.get("task")
                timestamp = entities.get("timestamp")
                response_text = schedule_reminder(task, timestamp, sender_number, get_credentials_from_db, scheduler)
            else:
                response_text = "❌ I couldn't understand that as a reminder. Please try again with a specific time and task."
            send_message(sender_number, response_text)
            set_user_session(sender_number, None)
            return

        if current_state == "awaiting_ai":
            send_message(sender_number, "🤖 Thinking...")
            current_session = get_user_session(sender_number)
            chat_history = current_session.get("chat_history", [])
            document_text = current_session.get("document_text")
            response_text, updated_history = get_chat_response(user_text, chat_history, document_text)
            current_session["chat_history"] = updated_history
            set_user_session(sender_number, current_session)
            send_message(sender_number, response_text)
            return
        
        if current_state == "awaiting_name":
            name = user_text.split()[0].title()
            create_or_update_user_in_db(sender_number, {"name": name, "expenses": [], "is_google_connected": False})
            set_user_session(sender_number, None)
            send_message(sender_number, f"✅ Got it! I’ll remember you as *{name}*.")
            time.sleep(1)
            if GOOGLE_REDIRECT_URI:
                try:
                    parsed_uri = urlparse(request.url_root)
                    base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    auth_link = f"{base_url}/google-auth?state={sender_number}"
                    auth_message = (
                        "To get the most out of me (like calendar events), connect your Google Account. "
                        f"Click here to connect: {auth_link}"
                    )
                    send_message(sender_number, auth_message)
                    time.sleep(2)
                except Exception as e:
                    print(f"Error generating Google Auth link: {e}")
            send_welcome_message(sender_number, name)
            return
        
        if isinstance(session_data, dict):
            state = session_data.get("state")
            if state == "awaiting_email_recipient":
                recipients = [email.strip() for email in user_text.split(',')]
                session_data["recipients"] = recipients
                session_data["state"] = "awaiting_email_subject"
                set_user_session(sender_number, session_data)
                send_message(sender_number, "👍 Got it. What's the subject of the email?")
                return

            elif state == "awaiting_email_subject":
                session_data["subject"] = user_text
                session_data["state"] = "awaiting_email_body"
                set_user_session(sender_number, session_data)
                send_message(sender_number, "📧 And what should the body of the email say? You can also ask me to generate it, e.g., 'Write a leave request.'")
                return

            elif state == "awaiting_email_body":
                if user_text_lower.startswith("write a"):
                    send_message(sender_number, "✍️ Generating the email body with AI...")
                    email_body = write_email_body_with_grok(user_text)
                    session_data["body"] = email_body
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, f"📝 Here's the draft:\n\n{email_body}\n\nDo you want me to `send` it, `edit` it, or `attach a file`?")
                else:
                    session_data["body"] = user_text
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, "Got the body. Do you want me to `send` it, `edit` it, or `attach a file`?")
                return

            elif state == "email_review":
                if user_text_lower == "send":
                    creds = get_credentials_from_db(sender_number)
                    if not creds:
                        send_message(sender_number, "❌ Sorry, your Google credentials are not valid. Please reconnect your account.")
                        set_user_session(sender_number, None)
                        return
                    send_message(sender_number, "🚀 Sending your email...")
                    response_text = send_email(creds, session_data["recipients"], session_data["subject"], session_data["body"], session_data.get("attachment_paths"))
                    for path in session_data.get("attachment_paths", []):
                        if os.path.exists(path):
                            os.remove(path)
                    set_user_session(sender_number, None)
                    send_message(sender_number, response_text)
                    return
                elif user_text_lower == "edit":
                    session_data["state"] = "awaiting_email_edit"
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, "✍️ What changes would you like to make to the draft? (e.g., 'make it more formal' or 'add a paragraph about the deadline')")
                    return
                elif user_text_lower == "attach a file":
                    session_data["state"] = "awaiting_email_attachment"
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, "📎 Please upload the file you would like to attach.")
                    return
                else:
                    send_message(sender_number, "I'm not sure what to do with that. Please reply with `send`, `edit`, or `attach a file`.")
                return

            elif state == "awaiting_email_attachment":
                if user_text_lower == "done":
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                    num_attachments = len(session_data.get("attachment_paths", []))
                    send_message(sender_number, f"✅ Got it. {num_attachments} file(s) attached. Do you want to `send` it, `edit` it, or `attach a file`?")
                else:
                    send_message(sender_number, "I'm not sure what to do with that. Please upload a file, or type `done` if you are finished.")
                return

            elif state == "awaiting_email_edit":
                send_message(sender_number, "📝 Applying your edits with AI...")
                original_body = session_data.get("body")
                edited_body = edit_email_body(original_body, user_text)
                if edited_body:
                    session_data["body"] = edited_body
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                    send_message(sender_number, f"✅ Here is the revised draft:\n\n{edited_body}\n\nDo you want me to `send` it, `edit` it, or `attach a file`?")
                else:
                    send_message(sender_number, "❌ Sorry, I couldn't apply those edits. Please try again.")
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                return

            elif state == "awaiting_more_attachments":
                if user_text_lower == "done":
                    session_data["state"] = "email_review"
                    set_user_session(sender_number, session_data)
                    num_attachments = len(session_data.get("attachment_paths", []))
                    send_message(sender_number, f"✅ Got it. {num_attachments} file(s) attached. Do you want to `send` it, `edit` it, or `attach a file`?")
                else:
                    send_message(sender_number, "I'm not sure what to do with that. Please upload a file, or type `done` if you are finished.")
                return
        
        send_message(sender_number, "I seem to have gotten confused. Let's start over.")
        return
    
    if user_text_lower in greetings:
        user_data = get_user_from_db(sender_number)
        if not user_data:
            set_user_session(sender_number, "awaiting_name")
            send_message(sender_number, "👋 Hi there! To personalize your experience, what should I call you?")
            return
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
        initial_session = {"state": "awaiting_ai", "chat_history": []}
        set_user_session(sender_number, initial_session)
        send_message(sender_number, "🤖 *AI Chat Active!* You can now ask me anything, or upload a document for me to read. \n\n_Type `menu` to exit this mode and clear my memory._")
        return
    elif user_text == "4":
        send_conversion_menu(sender_number)
        return
    elif user_text == "5":
        send_message(sender_number, "🤔 Live cricket score is no longer available as an option. Please select another menu item.")
        return
    elif user_text == "6":
        send_message(sender_number, "☁️ Fetching the current weather...")
        location = "Vijayawada"
        response_text = get_weather(location)
        send_message(sender_number, response_text)
        return
    elif user_text == "7":
        set_user_session(sender_number, "awaiting_currency")
        send_message(sender_number, "💱 *Currency Converter*\n\nWhat would you like to convert? (e.g., '100 USD to INR')")
        return
    elif user_text == "8":
        creds = get_credentials_from_db(sender_number)
        if creds:
            session_data = {"state": "awaiting_email_recipient"}
            set_user_session(sender_number, session_data)
            send_message(sender_number, "📧 *AI Email Assistant*\n\nWho are the recipients? (Emails separated by commas)")
        else:
            send_message(sender_number, "⚠️ To use the AI Email Assistant, you must first connect your Google account.")
        return
    elif user_text == "conv_pdf_to_text":
        set_user_session(sender_number, "awaiting_pdf_to_text")
        send_message(sender_number, "📂 Please upload the PDF file you want to convert to text.")
        return
    elif user_text == "conv_text_to_pdf":
        set_user_session(sender_number, "awaiting_text_to_pdf")
        send_message(sender_number, "📝 Please send me the text you want to convert to a PDF.")
        return
    elif user_text == "conv_pdf_to_word":
        set_user_session(sender_number, "awaiting_pdf_to_docx")
        send_message(sender_number, "📄 Please upload the PDF file you want to convert to Word.")
        return
    elif user_text == "conv_text_to_word":
        set_user_session(sender_number, "awaiting_text_to_word")
        send_message(sender_number, "📝 Please send me the text you want to convert to a Word file.")
        return
    elif user_text_lower == "cricket_refresh":
        send_message(sender_number, "🤔 Live cricket score is no longer available as an option. Please select another menu item.")
        return
    elif user_text_lower.startswith("cricket_match_"):
        send_message(sender_number, "🤔 Live cricket score is no longer available as an option. Please select another menu item.")
        return
    else:
        send_message(sender_number, "🤔 I couldn't understand that. Please try a different command or type `menu`.")

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
    df.to_excel(file_path, index=False, engine='openyxl')
    return file_path

def send_daily_briefing():
    print(f"--- Running Daily Briefing Job at {datetime.now()} ---")
    all_users = list(get_all_users_from_db())
    if not all_users:
        print("No users found. Skipping job.")
        return

    quote = get_daily_quote()
    history_fact = get_on_this_dayin_history()
    weather = get_conversational_weather()

    print(f"Found {len(all_users)} user(s) to send briefing to.")
    for user in all_users:
        user_id = user["_id"]
        user_name = user.get("name", "there")
        
        greeting = get_smart_greeting(user_name)
        
        template_name = "daily_briefing_v2"
        components = [
            {"type": "header", "parameters": [{"type": "text", "text": greeting}]},
            {"type": "body", "parameters": [
                {"type": "text", "text": quote},
                {"type": "text", "text": history_fact},
                {"type": "text", "text": weather}
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

    quote = get_daily_quote()
    history_fact = get_on_this_dayin_history()
    weather = get_conversational_weather()
    user_name = user.get("name", "Developer")
    greeting = get_smart_greeting(user_name)

    template_name = "daily_briefing_v2"
    components = [
        {"type": "header", "parameters": [{"type": "text", "text": greeting}]},
        {"type": "body", "parameters": [
            {"type": "text", "text": quote},
            {"type": "text", "text": history_fact},
            {"type": "text", "text": weather}
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
