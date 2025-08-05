# reminders.py
from datetime import datetime
from dateutil import parser as date_parser
import pytz
from messaging import send_template_message
from grok_ai import parse_reminder_with_grok
from google_calendar_integration import create_google_calendar_event
from app import get_user_from_db # Import the database function

# --- MODIFICATION START ---
# The separate scheduler instance has been REMOVED from this file.
# --- MODIFICATION END ---

def schedule_reminder(msg, user, get_creds_func, scheduler):
    """
    Schedules a reminder on WhatsApp and optionally on Google Calendar.
    It now receives the main scheduler instance from app.py.
    """
    task, timestamp_str = parse_reminder_with_grok(msg)

    if not task or not timestamp_str:
        return "❌ I couldn't understand that. Please try phrasing your reminder differently."

    try:
        # --- MODIFICATION START ---
        # Fetch user's saved timezone or default to 'Asia/Kolkata'
        user_data = get_user_from_db(user)
        user_timezone = user_data.get("timezone", "Asia/Kolkata")
        tz = pytz.timezone(user_timezone)
        # --- MODIFICATION END ---
        
        run_time = date_parser.parse(timestamp_str)

        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        if run_time < now:
            return f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) is in the past."

        template_name = "reminder_alert"
        components = [{
            "type": "body",
            "parameters": [{
                "type": "text",
                "text": task
            }]
        }]

        # --- MODIFICATION START ---
        # This now uses the main scheduler passed in from app.py
        scheduler.add_job(
            func=send_template_message,
            trigger='date',
            run_date=run_time,
            args=[user, template_name, components],
            id=f"reminder_{user}_{int(run_time.timestamp())}",
            replace_existing=True
        )
        # --- MODIFICATION END ---

        base_confirmation = f"✅ Reminder set for '{task}' on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
        gcal_confirmation = ""
        event_link_text = ""

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
