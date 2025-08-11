# services.py

import requests
import os
from datetime import datetime
import random

def get_indian_festival_today():
    """
    Checks if the current date corresponds to a major Indian festival.
    This is a simple implementation for demonstration. A more robust solution
    would use a library that calculates dates for lunar-based festivals.
    """
    today_str = datetime.now().strftime("%m-%d")
    
    # Dates for 2025
    festivals_2025 = {
        "01-14": "Makar Sankranti / Pongal",
        "01-26": "Republic Day",
        "03-14": "Holi",
        "03-30": "Eid-ul-Fitr",
        "08-03": "Friendship Day", # First Sunday of August 2025
        "08-15": "Independence Day",
        "08-19": "Raksha Bandhan",
        "08-26": "Janmashtami",
        "09-07": "Ganesh Chaturthi",
        "10-02": "Gandhi Jayanti",
        "10-21": "Dussehra",
        "11-09": "Diwali",
        "12-25": "Christmas Day"
    }
    
    return festivals_2025.get(today_str)


def get_daily_quote():
    """Fetches a random quote from the ZenQuotes API."""
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()
        data = response.json()[0]
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
        events = data.get("data", {}).get("Events", [])
        if len(events) > 3:
            return random.sample(events, 3)
        return events
    except Exception as e:
        print(f"On This Day in History error: {e}")
        return [{"text": "Could not retrieve a historical fact for today."}]

# *** FIX STARTS HERE ***
# The function now takes a 'city' parameter.
def get_raw_weather_data(city="Vijayawada"):
    """Fetches raw weather data from OpenWeatherMap."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    try:
        # The URL now uses the 'city' variable.
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # The error message now includes the city for easier debugging.
        print(f"Briefing weather error for city {city}: {e}")
        return None
# *** FIX ENDS HERE ***
