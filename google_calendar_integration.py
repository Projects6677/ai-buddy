# google_calendar_integration.py

import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import timedelta

# --- CONFIGURATION ---
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "https-your-app-url.com/google-auth/callback")

def get_google_auth_flow():
    """Starts the Google OAuth 2.0 flow."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def create_google_calendar_event(credentials, task, run_time):
    """
    Creates an event on the user's primary Google Calendar and returns a link.
    """
    try:
        service = build('calendar', 'v3', credentials=credentials)
        
        end_time = run_time + timedelta(minutes=30)

        # --- MODIFICATION START ---
        # The timezone is now taken from the `run_time` object passed in.
        event = {
            'summary': task,
            'description': 'Reminder set via AI Buddy.',
            'start': {
                'dateTime': run_time.isoformat(), # Use .isoformat() to include timezone
                'timeZone': str(run_time.tzinfo),
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': str(end_time.tzinfo),
            },
            'reminders': {
                'useDefault': True,
            },
        }
        # --- MODIFICATION END ---

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        event_link = created_event.get('htmlLink')
        confirmation_message = f"🗓️ Also added to your Google Calendar!"
        
        return confirmation_message, event_link

    except Exception as e:
        print(f"Google Calendar event creation error: {e}")
        return "❌ Failed to create Google Calendar event.", None
