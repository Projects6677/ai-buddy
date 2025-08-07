# reminders.py
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
from messaging import send_template_message
from google_calendar_integration import create_google_calendar_event
from apscheduler.schedulers.background import BackgroundScheduler # New import for clarity

# This function is now defined at the top level of the module,
# making it globally accessible and serializable by the scheduler.
def reminder_job(user, task, template_name, components):
    """
    Function to be executed by the scheduler to send a reminder message.
    It takes all necessary data as arguments.
    """
    print(f"[REMINDER TRIGGERED] Sending reminder to {user} for '{task}'")
    try:
        send_template_message(user, template_name, components)
    except Exception as e:
        print(f"❌ Failed to send reminder message: {e}")

def schedule_reminder(task, timestamp_str, user, get_creds_func, scheduler):
    """
    Schedules a reminder on WhatsApp and optionally on Google Calendar.
    """
    if not timestamp_str:
        return "❌ I couldn't understand the time for the reminder. Please try being more specific."

    if not task:
        task = "Reminder"

    try:
        tz = pytz.timezone('Asia/Kolkata')

        try:
            run_time = date_parser.parse(timestamp_str)
        except Exception as e:
            # More specific error message to help the user identify date parsing issues.
            print(f"❌ Failed to parse timestamp: {timestamp_str} — {e}")
            return "⚠️ Couldn’t understand the time format. Please try again with a clear date and time."

        # Ensure timezone awareness
        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)
        else:
            run_time = run_time.astimezone(tz)

        now = datetime.now(tz)

        if run_time < now:
            if run_time.date() == now.date():
                run_time += timedelta(days=1)
            else:
                return f"❌ The time you provided ({run_time.strftime('%A, %b %d at %I:%M %p')}) is in the past."

        print(f"[REMINDER DEBUG] Scheduling '{task}' at {run_time} for {user}")

        # WhatsApp message part
        template_name = "reminder_alert"
        components = [{
            "type": "body",
            "parameters": [{
                "type": "text",
                "text": task
            }]
        }]

        # The scheduler.add_job call now references the top-level reminder_job function
        # and passes the necessary data as arguments, which can be serialized.
        scheduler.add_job(
            func=reminder_job,
            trigger='date',
            run_date=run_time,
            id=f"reminder_{user}_{int(run_time.timestamp())}",
            replace_existing=True,
            args=[user, task, template_name, components]
        )

        base_confirmation = f"✅ Reminder set for *{task}* on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."
        gcal_confirmation = ""
        event_link_text = ""

        creds = get_creds_func(user)
        if creds:
            gcal_message, event_link = create_google_calendar_event(creds, task, run_time)
            gcal_confirmation = f"\n{gcal_message}"
            if event_link:
                event_link_text = f"\n🔗 [View Event]({event_link})"
        else:
            gcal_confirmation = "\n\n💡 Connect your Google Account to also save reminders to your calendar!"

        return f"{base_confirmation}{gcal_confirmation}{event_link_text}"

    except Exception as e:
        print(f"❌ Reminder scheduling error: {e}")
        return "❌ An unexpected error occurred while setting your reminder."
