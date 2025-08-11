# reminders.py
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import pytz
from messaging import send_template_message
from google_calendar_integration import create_google_calendar_event
import re
import time

def get_all_reminders(user, scheduler):
    """
    Fetches all scheduled jobs for a specific user and returns a structured list of dictionaries.
    """
    user_jobs = [job for job in scheduler.get_jobs() if job.id.startswith(f"reminder_{user}")]

    if not user_jobs:
        return []

    tz = pytz.timezone('Asia/Kolkata')
    reminders_list = []

    for job in user_jobs:
        try:
            task = job.args[2][0]['parameters'][0]['text']
            next_run = job.next_run_time.astimezone(tz).strftime('%a, %b %d at %I:%M %p')
            
            is_recurring = "Recurring" if hasattr(job.trigger, 'start_date') or type(job.trigger).__name__ == 'CronTrigger' else "One-Time"

            reminders_list.append({
                "id": job.id,
                "task": task,
                "next_run": next_run,
                "type": is_recurring
            })
        except (IndexError, KeyError, AttributeError):
            continue

    return reminders_list

def delete_reminder(job_id, scheduler):
    """
    Removes a specific job from the scheduler by its ID.
    """
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception as e:
        print(f"Error removing job {job_id}: {e}")
        return False


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
        day_match = re.search(r'(\d+)(?:st|nd|rd|th)?', rule_lower)
        if day_match:
            cron_args['day'] = int(day_match.group(1))
        else:
            cron_args['day'] = start_time.day
        cron_args['hour'] = start_time.hour
        cron_args['minute'] = start_time.minute
    
    return cron_args if cron_args else None


def schedule_reminder(full_text, time_expression, recurrence_rule, user, get_creds_func, scheduler):
    """
    Schedules a one-time or recurring reminder.
    """
    if not time_expression:
        return "❌ I couldn't understand the time for the reminder. Please try being more specific."

    # --- MODIFICATION: SMARTER TASK EXTRACTION ---
    # The task is the original text with the time expression and "remind me to" removed.
    task = full_text.lower().replace(time_expression.lower(), "").replace("remind me to", "").strip()
    if not task:
        task = "Reminder" # Fallback if the task is empty after stripping

    try:
        start_time = date_parser.parse(time_expression, fuzzy=True)
        tz = pytz.timezone('Asia/Kolkata')

        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)

        now = datetime.now(tz)
        
        template_name = "reminder_alert"
        components = [{"type": "body", "parameters": [{"type": "text", "text": task}]}]
        
        job_id = f"reminder_{user}_{int(time.time())}"
        
        cron_args = parse_recurrence_to_cron(recurrence_rule, start_time)
        job = None
        base_confirmation = ""

        if cron_args:
            job = scheduler.add_job(
                func=send_template_message,
                trigger='cron',
                args=[user, template_name, components],
                id=job_id,
                replace_existing=True,
                **cron_args
            )
            next_run = job.next_run_time.astimezone(tz).strftime('%A, %b %d at %I:%M %p')
            base_confirmation = f"✅ Recurring reminder set for '{task}' ({recurrence_rule}).\n\nThe next one is on *{next_run}*."
        else:
            if start_time < now:
                if start_time.date() == now.date():
                    start_time += timedelta(days=1)
                else:
                    return f"❌ The time you provided ({start_time.strftime('%A, %b %d at %I:%M %p')}) is in the past."
            
            job = scheduler.add_job(
                func=send_template_message,
                trigger='date',
                run_date=start_time,
                args=[user, template_name, components],
                id=job_id,
                replace_existing=True
            )
            base_confirmation = f"✅ Reminder set for '{task}' on {start_time.strftime('%A, %b %d at %I:%M %p')}."

        gcal_confirmation = ""
        event_link_text = ""
        creds = get_creds_func(user)
        if creds:
            gcal_first_run = job.next_run_time if job else start_time
            gcal_message, event_link = create_google_calendar_event(creds, task, gcal_first_run)
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
