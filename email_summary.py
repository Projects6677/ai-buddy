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

def send_email_summary_for_user(user_id, user_name, credentials):
    """
    Fetches, summarizes, and sends the daily email summary for a single user using a template.
    """
    print(f"--- Generating email summary for {user_name} ({user_id}) ---")
    
    emails = get_recent_emails(credentials)
    
    if emails is None:
        # Send an error message if Gmail access fails
        send_message(user_id, "⚠️ Sorry, I couldn't access your Gmail account to create your summary. Please try reconnecting your account using the `.reconnect` command.")
        return

    if not emails:
        # Send a specific template if there are no new emails
        template_name = "daily_email_summary_v1" # Use the same template for consistency
        components = [
            {"type": "header", "parameters": [{"type": "text", "text": "📧 Your 9 AM Email Summary"}]},
            {"type": "body", "parameters": [
                {"type": "text", "text": user_name},
                {"type": "text", "text": "Your inbox is clear! ✨"},
                {"type": "text", "text": "No new unread emails in the last 24 hours."},
                {"type": "text", "text": "Great job staying on top of your inbox."}
            ]}
        ]
        send_template_message(user_id, template_name, components)
        return
        
    # Generate the structured summary from the AI
    summary_data = generate_email_summary(emails, user_name)
    
    # Send the template with the structured data
    template_name = "daily_email_summary_v1"
    components = [
        {"type": "header", "parameters": [{"type": "text", "text": "📧 Your 9 AM Email Summary"}]},
        {"type": "body", "parameters": [
            {"type": "text", "text": user_name},
            {"type": "text", "text": summary_data.get("highlight", "N/A")},
            {"type": "text", "text": summary_data.get("other_updates", "N/A")},
            {"type": "text", "text": summary_data.get("suggestion", "N/A")}
        ]}
    ]
    send_template_message(user_id, template_name, components)
    print(f"--- Email summary sent to {user_name} ({user_id}) ---")

