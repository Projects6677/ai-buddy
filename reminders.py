# reminders.py
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil import parser as date_parser
from datetime import datetime, timedelta
import os
from email_sender import send_email

# NOTE: The get_credentials_from_db and send_message functions are passed from app.py
# to avoid circular imports.

def reminder_job(task, sender_number, send_message):
    """The job function that sends the reminder message."""
    send_message(sender_number, f"🔔 *Reminder:* {task}")

def schedule_reminder(task, timestamp, sender_number, get_credentials_from_db, scheduler):
    """Schedules a new reminder using APScheduler."""
    if not timestamp:
        return "❌ I need a specific date and time to set a reminder. Please try again with a phrase like 'remind me to call mom tomorrow at 5pm'."
    
    try:
        reminder_time = date_parser.parse(timestamp)
        tz = pytz.timezone('Asia/Kolkata')
        if reminder_time.tzinfo is None:
            reminder_time = tz.localize(reminder_time)
        
        # Check if the time is in the past
        now = datetime.now(tz)
        if reminder_time < now:
            return "❌ I can't set a reminder for a time that has already passed. Please provide a future date and time."
        
        scheduler.add_job(
            func=reminder_job,
            trigger='date',
            run_date=reminder_time,
            args=[task, sender_number, send_message],
            id=f"reminder_job_{sender_number}_{reminder_time.isoformat()}"
        )
        
        return f"✅ Got it! I've scheduled a reminder for you: *'{task}'* on {reminder_time.strftime('%B %d at %I:%M %p')}"
    
    except Exception as e:
        print(f"Error scheduling reminder: {e}")
        return "❌ Sorry, I had trouble understanding that date and time. Please try a different format."

def email_scheduler_job(recipients, subject, body, attachment_paths, sender_number, get_credentials_from_db, send_message):
    """The job function that sends the scheduled email."""
    try:
        creds = get_credentials_from_db(sender_number)
        if not creds:
            send_message(sender_number, "❌ Sorry, your Google credentials are not valid. The scheduled email was not sent.")
            return

        response_text = send_email(creds, recipients, subject, body, attachment_paths)
        send_message(sender_number, response_text)
    except Exception as e:
        print(f"Error sending scheduled email: {e}")
        send_message(sender_number, "❌ An error occurred while trying to send your scheduled email.")
    finally:
        if attachment_paths:
            for path in attachment_paths:
                if os.path.exists(path):
                    os.remove(path)

def schedule_email(recipients, subject, body, attachment_paths, timestamp, sender_number, get_credentials_from_db, scheduler, send_message):
    """Schedules a new email to be sent using APScheduler."""
    try:
        email_time = date_parser.parse(timestamp)
        tz = pytz.timezone('Asia/Kolkata')
        if email_time.tzinfo is None:
            email_time = tz.localize(email_time)
        
        # Check if the time is in the past
        now = datetime.now(tz)
        if email_time < now:
            return "❌ I can't schedule an email to be sent at a time that has already passed. Please provide a future date and time."

        scheduler.add_job(
            func=email_scheduler_job,
            trigger='date',
            run_date=email_time,
            args=[recipients, subject, body, attachment_paths, sender_number, get_credentials_from_db, send_message],
            id=f"email_job_{sender_number}_{email_time.isoformat()}"
        )
        
        return f"✅ Got it! I've scheduled your email to be sent on {email_time.strftime('%B %d at %I:%M %p')}."
    
    except Exception as e:
        print(f"Error scheduling email: {e}")
        return "❌ Sorry, I had trouble understanding that date and time. Please try a different format to schedule your email."
