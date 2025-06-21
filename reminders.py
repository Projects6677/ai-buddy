from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dateutil import parser
import pytz
from messaging import send_message  # make sure send_message is not inside __main__

scheduler = BackgroundScheduler()
scheduler.start()

# Store user reminders in memory (you can upgrade to DB/file later)
reminders = []

def schedule_reminder(msg, user):
    try:
        parts = msg.lower().split("remind me to")[1].strip().split(" at ")
        task = parts[0]
        time_string = parts[1]

        # Parse time and add today's date
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        run_time = parser.parse(time_string, default=now)

        # Handle past times (assume next day)
        if run_time < now:
            run_time = run_time.replace(day=run_time.day + 1)

        # Schedule the reminder
        scheduler.add_job(
            func=send_message,
            trigger='date',
            run_date=run_time,
            args=[user, f"⏰ Reminder: {task}"],
            id=f"{user}-{task}-{run_time.timestamp()}",
            replace_existing=True
        )

        return f"✅ Reminder set for *{task}* at *{run_time.strftime('%I:%M %p')}*."

    except Exception as e:
        print("Reminder error:", e)
        return "❌ Could not set reminder. Please use: Remind me to [task] at [time]"

