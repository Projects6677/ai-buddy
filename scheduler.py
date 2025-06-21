import datetime

# In a real version, you'd store and schedule this
def schedule_reminder(msg, user):
    # Example input: "Remind me to call mom at 5pm"
    try:
        parts = msg.lower().split("remind me to")[1].strip().split(" at ")
        task = parts[0]
        time = parts[1]
        # Simulate: In real version, store this and check periodically
        return f"⏰ Reminder set!\nI'll remind you to *{task}* at *{time}*. (Simulated)"
    except:
        return "❌ Invalid format. Use: Remind me to [task] at [time]"
