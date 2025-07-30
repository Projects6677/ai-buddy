from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dateutil import parser as date_parser
import pytz
from messaging import send_message
from grok_ai import parse_reminder_with_grok # <-- IMPORT the AI parser

# This scheduler instance is created here, but it's better practice
# to have a single instance in your main app.py. For now, this works.
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
if not scheduler.running:
    scheduler.start()

def schedule_reminder(msg, user):
    """
    Schedules a reminder using AI to parse the user's message.
    """
    # Use the AI to parse the task and time from the user's message
    task, timestamp_str = parse_reminder_with_grok(msg)

    if not task or not timestamp_str:
        return "❌ I couldn't quite understand that. Please try phrasing your reminder differently, for example: 'Remind me to call Mom tomorrow at 5 PM'."

    try:
        # The AI provides a clean timestamp, which is easy to parse
        tz = pytz.timezone('Asia/Kolkata')
        run_time = date_parser.parse(timestamp_str)

        # Ensure the datetime object is timezone-aware
        if run_time.tzinfo is None:
            run_time = tz.localize(run_time)

        now = datetime.now(tz)
        if run_time < now:
            return f"❌ The time you provided ({run_time.strftime('%I:%M %p')}) seems to be in the past. Please specify a future time."

        # Schedule the reminder job
        scheduler.add_job(
            func=send_message,
            trigger='date',
            run_date=run_time,
            args=[user, f"⏰ Reminder: {task}"],
            id=f"reminder_{user}_{int(run_time.timestamp())}",
            replace_existing=True
        )

        return f"✅ Reminder set! I'll ping you about '{task}' on *{run_time.strftime('%A, %b %d at %I:%M %p')}*."

    except (date_parser.ParserError, ValueError) as e:
        print(f"Reminder parsing error after Grok: {e}")
        return "❌ An unexpected error occurred while setting your reminder."

