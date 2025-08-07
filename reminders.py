# reminders.py
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
from messaging import send_template_message
# REMOVED: No longer importing from grok_ai
# from grok_ai import parse_reminder_with_grok 
from google_calendar_integration import create_google_calendar_event

# MODIFICATION: The function now accepts task and timestamp_str directly
def schedule_reminder(task, timestamp_str, user, get_creds_func, scheduler):
    """
    Schedules a reminder on WhatsApp and optionally on Google Calendar.
    """
    # REMOVED: The parsing is now done in app.py by the intent router
    # task, timestamp_str = parse_reminder_with_grok(msg)

    if not timestamp_str:
        return "❌ I couldn't understand the time for the reminder. Please try being more specific."

    if not task:
        task = "Reminder" # Default task if AI can't find one

    try:
        tz = pytz.timezone('Asia/Kolkata')
        run_time = date_parser.parse(timestamp_str)

        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        
        if run_time < now:
            if run_time.date() == now.date():
                run_time += timedelta(days=1)
            else:
                return f"❌ The time you provided ({run_time.strftime('%A, %b %d at %I:%M %p')}) is in the past."

        template_name = "reminder_alert"
        components = [{
            "type": "body",
            "parameters": [{
                "type": "text",
                "text": task
            }]
        }]

        scheduler.add_job(
            func=send_template_message,
            trigger='date',
            run_date=run_time,
            args=[user, template_name, components],
            id=f"reminder_{user}_{int(run_time.timestamp())}",
            replace_existing=True
        )

        base_confirmation = f"✅ Reminder set for '{task}' on {run_time.strftime('%A, %b %d at %I:%M %p')}."
        gcal_confirmation = ""
        event_link_text = ""

        creds = get_creds_func(user)
        if creds:
            gcal_message, event_link = create_google_calendar_event(creds, task, run_time)
            gcal_confirmation = f"\n{gcal_message}"
            if event_link:
                event_link_text = f"\n\n🔗 View Event: {event_link}"
        else:
            gcal_confirmation = "\n\n💡 Connect your Google Account to also save reminders to your calendar!"

        return f"{base_confirmation}{gcal_confirmation}{event_link_text}"

    except Exception as e:
        print(f"Reminder scheduling error: {e}")
        return "❌ An unexpected error occurred while setting your reminder."
