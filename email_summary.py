# 
from googleapiclient.discovery import build
import base64
from datetime import datetime, timedelta
import pytz

from messaging import send_message
from grok_ai import generate_email_summary

def get_recent_emails(credentials):
    """Fetches unread emails from the last 24 hours using the Gmail API."""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        
        # Define the query for unread emails in the last 24 hours
        query = 'is:unread in:inbox after:' + (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
        
        # Get the list of message IDs
        response = service.users().messages().list(userId='me', q=query).execute()
        messages = response.get('messages', [])
        
        if not messages:
            return []

        email_list = []
        # Get details for each message (up to a limit of 15 to keep it concise)
        for msg in messages[:15]:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            snippet = msg_data.get('snippet', '')
            
            email_list.append({
                "from": sender,
                "subject": subject,
                "snippet": snippet.strip()
            })
            
        return email_list

    except Exception as e:
        print(f"Error fetching recent emails: {e}")
        return None # Return None to indicate an error

def send_email_summary_for_user(user_id, user_name, credentials):
    """
    Fetches, summarizes, and sends the daily email summary for a single user.
    This function is designed to be called by the main scheduler job.
    """
    print(f"--- Generating email summary for {user_name} ({user_id}) ---")
    
    # 1. Fetch recent emails
    emails = get_recent_emails(credentials)
    
    if emails is None:
        # An error occurred during fetching
        send_message(user_id, "⚠️ Sorry, I couldn't access your Gmail account to create your summary. Please try reconnecting your account using the `.reconnect` command.")
        return

    if not emails:
        # No unread emails in the last 24 hours
        send_message(user_id, "📧 Good morning! You have no new unread emails in the last 24 hours. Your inbox is clear! ✨")
        return
        
    # 2. Generate the summary using AI
    summary_text = generate_email_summary(emails, user_name)
    
    # 3. Send the summary
    send_message(user_id, summary_text)
    print(f"--- Email summary sent to {user_name} ({user_id}) ---")
