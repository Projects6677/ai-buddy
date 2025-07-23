# google_calendar_integration.py

import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import timedelta

# --- CONFIGURATION ---
# IMPORTANT: Download your client_secret.json from Google Cloud Console and place it here.
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
# This should be the publicly accessible URL of your webhook + /google-auth/callback
# For local testing, you might use ngrok and set this URL dynamically.
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "https_your_app_url.com/google-auth/callback")

def get_google_auth_flow():
    """Starts the Google OAuth 2.0 flow."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def get_credentials(sender_number):
    """
    Gets stored user credentials. Returns None if not found or invalid.
    """
    token_dir = "user_tokens"
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)

    token_path = os.path.join(token_dir, f"{sender_number}.pickle")

    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)

    # Check if credentials are valid and refresh if necessary
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save the refreshed credentials
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)

    if creds and creds.valid:
        return creds
    
    return None

def save_credentials(sender_number, credentials):
    """Saves user credentials to a file."""
    token_dir = "user_tokens"
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)
        
    token_path = os.path.join(token_dir, f"{sender_number}.pickle")
    with open(token_path, 'wb') as token_file:
        pickle.dump(credentials, token_file)

def create_google_calendar_event(credentials, task, run_time):
    """
    Creates an event on the user's primary Google Calendar.
    """
    try:
        service = build('calendar', 'v3', credentials=credentials)
        
        end_time = run_time + timedelta(minutes=30)

        # --- MODIFICATION START ---
        # The fix is to provide a timezone-naive datetime string to the API
        # and specify the timezone separately. This avoids ambiguity.
        event = {
            'summary': task,
            'description': 'Reminder set via AI Buddy.',
            'start': {
                'dateTime': run_time.strftime('%Y-%m-%dT%H:%M:%S'), # Naive time string
                'timeZone': 'Asia/Kolkata', # Explicit timezone
            },
            'end': {
                'dateTime': end_time.strftime('%Y-%m-%dT%H:%M:%S'), # Naive time string
                'timeZone': 'Asia/Kolkata', # Explicit timezone
            },
            'reminders': {
                'useDefault': True,
            },
        }
        # --- MODIFICATION END ---

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        # The confirmation message uses the original 'run_time' object, which is correct.
        return f"✅ Event '{task}' created in your Google Calendar for *{run_time.strftime('%A, %b %d at %I:%M %p')}*."

    except Exception as e:
        print(f"Google Calendar event creation error: {e}")
        return "❌ Sorry, I failed to create the event in your Google Calendar."
