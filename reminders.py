# reminders.py
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
from messaging import send_template_message
from google_calendar_integration import create_google_calendar_event

# MODIFICATION: The function now accepts a natural time_expression
def schedule_reminder(task, time_expression, user, get_creds_func, scheduler):
    """
    Schedules a reminder on WhatsApp and optionally on Google Calendar.
    It now parses the natural time expression itself.
    """
    if not time_expression:
        return "❌ I couldn't understand the time for the reminder. Please try being more specific."

    if not task:
        task = "Reminder"

    try:
        # Use the powerful dateutil parser to understand the natural language time
        run_time = date_parser.parse(time_expression)
        
        tz = pytz.timezone('Asia/Kolkata')

        # If the parsed time has no timezone, assume it's for the local timezone
        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        
        if run_time < now:
            # If the time is in the past, but on the same day, assume it's for the next day
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

    except date_parser.ParserError:
        return f"❌ Sorry, I had trouble understanding the date and time '{time_expression}'. Please try a different format."
    except Exception as e:
        print(f"Reminder scheduling error: {e}")
        return "❌ An unexpected error occurred while setting your reminder."
