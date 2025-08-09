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
        # Return both the quote and the author
        return data['q'], data['a']
    except Exception as e:
        print(f"Error fetching daily quote: {e}")
        return "The best way to predict the future is to create it.", "Peter Drucker"

def get_on_this_day_in_history():
    """Fetches a few historical events for the current day."""
    try:
        now = datetime.now()
        month = now.month
        day = now.day
        url = f"https://today.zenquotes.io/api/{month}/{day}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Get up to 3 random events from the list of events
        events = data.get("data", {}).get("Events", [])
        if len(events) > 3:
            return random.sample(events, 3)
        return events
    except Exception as e:
        print(f"On This Day in History error: {e}")
        return [{"text": "Could not retrieve a historical fact for today."}]

def get_raw_weather_data(city="Vijayawada"):
    """Fetches raw weather data from OpenWeatherMap."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Briefing weather error: {e}")
        return None
