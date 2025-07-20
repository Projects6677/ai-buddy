# email_sender.py
import os
import smtplib
from email.message import EmailMessage
import mimetypes # Used to guess the file type

SENDER_EMAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def send_email(recipient_emails, subject, body, attachment_path=None):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return "Error: Email credentials are not configured on the server."

    if not isinstance(recipient_emails, list):
        recipient_emails = [recipient_emails]

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(recipient_emails)

        # --- ATTACHMENT LOGIC ---
        if attachment_path and os.path.exists(attachment_path):
            # Guess the MIME type of the file
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream' # Generic fallback
            maintype, subtype = ctype.split('/', 1)
            
            with open(attachment_path, 'rb') as fp:
                msg.add_attachment(fp.read(),
                                   maintype=maintype,
                                   subtype=subtype,
                                   filename=os.path.basename(attachment_path))
        # --- END ATTACHMENT LOGIC ---

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        recipient_str = ", ".join(f"*{email}*" for email in recipient_emails)
        confirmation_message = f"✅ Email successfully sent to {recipient_str}."
        if attachment_path:
            confirmation_message += " with 1 attachment."
        return confirmation_message

    except Exception as e:
        print(f"Email sending error: {e}")
        return "❌ Sorry, I failed to send the email. Please check the server logs."
