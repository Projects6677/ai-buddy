# email_sender.py
import os
import smtplib
from email.message import EmailMessage

SENDER_EMAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def send_email(recipient_email, subject, body):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return "Error: Email credentials are not configured on the server."

    try:
        # Create the email message
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        return f"✅ Email successfully sent to *{recipient_email}*."

    except Exception as e:
        print(f"Email sending error: {e}")
        return "❌ Sorry, I failed to send the email. Please check the server logs or credentials."
