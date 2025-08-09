# reminders.py
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
from messaging import send_template_message
from google_calendar_integration import create_google_calendar_event
import re
import time # MODIFICATION: Added the missing import

def parse_recurrence_to_cron(recurrence_rule, start_time):
    """
    Converts a natural language recurrence rule into cron arguments for apscheduler.
    """
    if not recurrence_rule:
        return None

    rule_lower = recurrence_rule.lower()
    cron_args = {}

    if 'every day' in rule_lower:
        cron_args['hour'] = start_time.hour
        cron_args['minute'] = start_time.minute
    elif 'every week' in rule_lower or any(day in rule_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
        cron_args['day_of_week'] = start_time.weekday()
        cron_args['hour'] = start_time.hour
        cron_args['minute'] = start_time.minute
    elif 'every month' in rule_lower:
        # Find the day of the month, e.g., "1st", "15th"
        day_match = re.search(r'(\d+)(?:st|nd|rd|th)?', rule_lower)
        if day_match:
            cron_args['day'] = int(day_match.group(1))
        else:
            cron_args['day'] = start_time.day # Default to the same day of the month
        cron_args['hour'] = start_time.hour
        cron_args['minute'] = start_time.minute
    
    return cron_args if cron_args else None


def schedule_reminder(task, time_expression, recurrence_rule, user, get_creds_func, scheduler):
    """
    Schedules a one-time or recurring reminder.
    """
    if not time_expression:
        return "❌ I couldn't understand the time for the reminder. Please try being more specific."

    if not task:
        task = "Reminder"

    try:
        # Use the powerful dateutil parser to understand the natural language time
        start_time = date_parser.parse(time_expression)
        
        tz = pytz.timezone('Asia/Kolkata')

        # If the parsed time has no timezone, assume it's for the local timezone
        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)

        now = datetime.now(tz)
        
        # Ensure the first run time is in the future
        if start_time < now:
            # If the time is in the past, but on the same day, assume it's for the next day
            if start_time.date() == now.date():
                start_time += timedelta(days=1)
            # This logic might need adjustment for recurring reminders, but is a safe default
            elif not recurrence_rule:
                 return f"❌ The time you provided ({start_time.strftime('%A, %b %d at %I:%M %p')}) is in the past."


        template_name = "reminder_alert"
        components = [{"type": "body", "parameters": [{"type": "text", "text": task}]}]
        
        job_id = f"reminder_{user}_{int(time.time())}" # Use timestamp for a unique ID
        
        cron_args = parse_recurrence_to_cron(recurrence_rule, start_time)

        if cron_args:
            # This is a recurring reminder
            scheduler.add_job(
                func=send_template_message,
                trigger='cron',
                args=[user, template_name, components],
                id=job_id,
                replace_existing=True,
                **cron_args
            )
            base_confirmation = f"✅ Recurring reminder set for '{task}' ({recurrence_rule})."
        else:
            # This is a one-time reminder
            scheduler.add_job(
                func=send_template_message,
                trigger='date',
                run_date=start_time,
                args=[user, template_name, components],
                id=job_id,
                replace_existing=True
            )
            base_confirmation = f"✅ Reminder set for '{task}' on {start_time.strftime('%A, %b %d at %I:%M %p')}."

        # Google Calendar integration does not support recurrence in this simple setup
        # It will only add the first instance of the event.
        gcal_confirmation = ""
        event_link_text = ""
        creds = get_creds_func(user)
        if creds:
            gcal_message, event_link = create_google_calendar_event(creds, task, start_time)
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
