# services.py

import requests
import os
from datetime import datetime
import random

def get_daily_quote():
    """Fetches a random quote from the ZenQuotes API."""
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()
        data = response.json()[0]
        return f"\"{data['q']}\" - {data['a']}"
    except Exception as e:
        print(f"Error fetching daily quote: {e}")
        return "\"The best way to predict the future is to create it.\" - Peter Drucker"

def get_briefing_weather(city="Vijayawada"):
    """DEPRECATED: This function is no longer used. The new get_conversational_weather is used instead."""
    # This function is kept for potential future use but is not called by the daily briefing.
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather update unavailable."
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        emoji = {"01":"☀️","02":"⛅️","03":"☁️","04":"☁️","09":"🌧️","10":"🌦️","11":"⛈️","13":"❄️","50":"🌫️"}.get(data["weather"][0]["icon"][:2], "🌡️")
        description = data['weather'][0]['description'].title()
        temp = data['main']['temp']
        return f"{emoji} *{data['name']}:* {temp}°C, {description}"
    except Exception as e:
        print(f"Briefing weather error: {e}")
        return "Weather update unavailable."

def get_on_this_day_in_history():
    """Fetches a historical event for the current day from the ZenQuotes On This Day API."""
    try:
        now = datetime.now()
        month = now.month
        day = now.day
        url = f"https://today.zenquotes.io/api/{month}/{day}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Get a random event from the list of events
        event = random.choice(data.get("data", {}).get("Events", []))
        return event.get("text", "No historical fact found for today.")
    except Exception as e:
        print(f"On This Day in History error: {e}")
        return "Could not retrieve a historical fact for today."
