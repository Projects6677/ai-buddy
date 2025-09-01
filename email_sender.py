# email_sender.py
import os
import base64
from email.message import EmailMessage
import mimetypes
from googleapiclient.discovery import build

def create_message(sender, to, subject, body, attachment_paths=None):
    """Creates an email message object."""
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject

    if attachment_paths and isinstance(attachment_paths, list):
        for path in attachment_paths:
            if os.path.exists(path):
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                
                with open(path, 'rb') as fp:
                    message.add_attachment(fp.read(),
                                       maintype=maintype,
                                       subtype=subtype,
                                       filename=os.path.basename(path))
    return message

def send_email(credentials, recipient_emails, subject, body, attachment_paths=None):
    """
    Sends an email using the user's Gmail account via the Gmail API.
    """
    try:
        # From email_sender.py
        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        
        # Get the user's own email address to use as the 'From' field
        user_email = service.users().getProfile(userId='me').execute().get('emailAddress')
        
        if not isinstance(recipient_emails, list):
            recipient_emails = [recipient_emails]
        
        email_message = create_message(user_email, ", ".join(recipient_emails), subject, body, attachment_paths)
        
        encoded_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode()
        create_message_body = {'raw': encoded_message}
        
        # Send the email
        service.users().messages().send(userId="me", body=create_message_body).execute()
        
        recipient_str = ", ".join(f"*{email}*" for email in recipient_emails)
        confirmation_message = f"✅ Email successfully sent from your account to {recipient_str}."
        if attachment_paths and len(attachment_paths) > 0:
            confirmation_message += f" with {len(attachment_paths)} attachment(s)."
        return confirmation_message

    except Exception as e:
        print(f"Gmail API sending error: {e}")
        return "❌ Sorry, I failed to send the email. Please ensure you have granted Gmail permissions."
