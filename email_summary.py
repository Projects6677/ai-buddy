# email_summary.py
from googleapiclient.discovery import build
import base64
from datetime import datetime, timedelta
import pytz

from messaging import send_message, send_template_message
from grok_ai import generate_email_summary

def get_recent_emails(credentials):
    """Fetches unread emails from the last 24 hours using the Gmail API."""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        query = 'is:unread in:inbox after:' + (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
        response = service.users().messages().list(userId='me', q=query).execute()
        messages = response.get('messages', [])
        
        if not messages:
            return []

        email_list = []
        for msg in messages[:15]:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            snippet = msg_data.get('snippet', '')
            
            email_list.append({"from": sender, "subject": subject, "snippet": snippet.strip()})
            
        return email_list

    except Exception as e:
        print(f"Error fetching recent emails: {e}")
        return None

def send_email_summary_notification(user_id, user_name):
    """
    Sends the pre-approved template to notify the user their summary is ready.
    This is called by the main scheduler.
    """
    print(f"--- Sending email summary notification to {user_name} ({user_id}) ---")
    template_name = "email_summary_notification"
    components = [{"type": "body", "parameters": [{"type": "text", "text": user_name}]}]
    send_template_message(user_id, template_name, components)

def generate_and_send_full_summary(user_id, user_name, credentials):
    """
    Fetches emails, generates the full AI summary, and sends it as a text message.
    This is triggered by the user's reply to the notification.
    """
    send_message(user_id, "Got it! Generating your email summary now, this may take a moment...")
    
    emails = get_recent_emails(credentials)
    
    if emails is None:
        send_message(user_id, "⚠️ Sorry, I couldn't access your Gmail account to create your summary. Please try reconnecting your account using the `.reconnect` command.")
        return

    if not emails:
        send_message(user_id, "You have no new unread emails in the last 24 hours. Your inbox is clear! ✨")
        return
        
    summary_text = generate_email_summary(emails, user_name)
    send_message(user_id, summary_text)
    print(f"--- Full email summary sent to {user_name} ({user_id}) ---")

