# email_sender.py
import os
import smtplib
from email.message import EmailMessage
import mimetypes

SENDER_EMAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def send_email(recipient_emails, subject, body, attachment_paths=None):
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

        # --- UPDATED ATTACHMENT LOGIC FOR MULTIPLE FILES ---
        if attachment_paths and isinstance(attachment_paths, list):
            for path in attachment_paths:
                if os.path.exists(path):
                    ctype, encoding = mimetypes.guess_type(path)
                    if ctype is None or encoding is not None:
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    
                    with open(path, 'rb') as fp:
                        msg.add_attachment(fp.read(),
                                           maintype=maintype,
                                           subtype=subtype,
                                           filename=os.path.basename(path))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        recipient_str = ", ".join(f"*{email}*" for email in recipient_emails)
        confirmation_message = f"✅ Email successfully sent to {recipient_str}."
        if attachment_paths and len(attachment_paths) > 0:
            confirmation_message += f" with {len(attachment_paths)} attachment(s)."
        return confirmation_message

    except Exception as e:
        print(f"Email sending error: {e}")
        return "❌ Sorry, I failed to send the email. Please check the server logs."
