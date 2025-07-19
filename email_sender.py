# email_sender.py
import os
import smtplib
from email.message import EmailMessage

SENDER_EMAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def send_email(recipient_emails, subject, body):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return "Error: Email credentials are not configured on the server."

    # Ensure recipient_emails is a list
    if not isinstance(recipient_emails, list):
        recipient_emails = [recipient_emails]

    try:
        # Create the email message
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        # The 'To' field can be a comma-separated string of addresses
        msg['To'] = ", ".join(recipient_emails)

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        # Format recipient list for the confirmation message
        recipient_str = ", ".join(f"*{email}*" for email in recipient_emails)
        return f"✅ Email successfully sent to {recipient_str}."

    except Exception as e:
        print(f"Email sending error: {e}")
        return "❌ Sorry, I failed to send the email. Please check the server logs."
