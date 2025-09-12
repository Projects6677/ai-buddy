# google_calendar_integration.py

import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import timedelta
import json
import io

# --- CONFIGURATION ---
CLIENT_SECRETS_JSON = {
    "web": {
        "client_id": "316927646892-jdgnktunhf55reb5teb5nefcdo824bdl.apps.googleusercontent.com",
        "project_id": "ai-b-466813",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["https://ai-buddy-bx6w.onrender.com/google-auth/callback"]
    }
}
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/userinfo.email'
]
REDIRECT_URI = "https://ai-buddy-bx6w.onrender.com/google-auth/callback"

def get_google_auth_flow():
    """Starts the Google OAuth 2.0 flow."""
    # Use from_client_config to pass the dictionary directly
    flow = Flow.from_client_config(
        CLIENT_SECRETS_JSON,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def create_google_calendar_event(credentials, task, run_time):
    """
    Creates an event on the user's primary Google Calendar and returns a link.
    """
    try:
        service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        
        end_time = run_time + timedelta(minutes=30)

        event = {
            'summary': task,
            'description': f"Reminder set for {run_time.strftime('%I:%M %p')} via AI Buddy.",
            'start': {
                'dateTime': run_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Asia/Kolkata',
            },
            'reminders': {
                'useDefault': True,
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        event_link = created_event.get('htmlLink')
        confirmation_message = f"🗓 Also added to your Google Calendar!"
        
        return confirmation_message, event_link

    except Exception as e:
        print(f"Google Calendar event creation error: {e}")
        return "❌ Failed to create Google Calendar event.", None
