# reminders.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dateutil import parser as date_parser
import pytz
from messaging import send_message
from grok_ai import parse_reminder_with_grok
from google_calendar_integration import create_google_calendar_event

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
if not scheduler.running:
    scheduler.start()

def schedule_reminder(msg, user, get_creds_func):
    """
    Schedules a reminder on WhatsApp and optionally on Google Calendar.
    `get_creds_func` is a function passed from app.py to get credentials from the DB.
    """
    task, timestamp_str = parse_reminder_with_grok(msg)

    if not task or not timestamp_str:
        return "❌ I couldn't understand that. Please try phrasing your reminder differently."

    try:
        tz = pytz.timezone('Asia/Kolkata')
        run_time = date_parser.parse(timestamp_str)

        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        if run_time < now:
            return f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) is in the past."

        # Schedule the WhatsApp reminder
        scheduler.add_job(
            func=send_message,
            trigger='date',
            run_date=run_time,
            args=[user, f"⏰ Reminder: {task}"],
            id=f"reminder_{user}_{int(run_time.timestamp())}",
            replace_existing=True
        )

        base_confirmation = f"✅ Reminder set for '{task}' on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
        gcal_confirmation = ""
        event_link_text = ""

        # Check for Google Calendar credentials using the passed function
        creds = get_creds_func(user)
        if creds:
            gcal_message, event_link = create_google_calendar_event(creds, task, run_time)
            gcal_confirmation = f"\n{gcal_message}"
            if event_link:
                event_link_text = f"\n\n🔗 View Event: {event_link}"
        else:
            gcal_confirmation = "\n\n💡 _Connect your Google Account to also save reminders to your calendar!_"

        return f"{base_confirmation}{gcal_confirmation}{event_link_text}"

    except Exception as e:
        print(f"Reminder scheduling error: {e}")
        return "❌ An unexpected error occurred while setting your reminder."
