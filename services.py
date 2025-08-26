# services.py

import requests
import os
from datetime import datetime
import random

def get_indian_festival_today():
    """
    Checks for a major Indian festival on the current date using a live API.
    """
    api_key = os.environ.get("HOLIDAY_API_KEY")
    if not api_key:
        print("Holiday API key not found. Skipping festival check.")
        return None

    try:
        now = datetime.now()
        country = "IN" # ISO 3166-1 alpha-2 country code for India
        
        url = f"https://holidays.abstractapi.com/v1/?api_key={api_key}&country={country}&year={now.year}&month={now.month}&day={now.day}"
        
        response = requests.get(url)
        response.raise_for_status()
        holidays = response.json()

        if not holidays:
            return None

        # Prioritize returning a religious or national holiday if one exists
        for holiday in holidays:
            # The API categorizes holidays, we look for the most relevant ones
            if holiday.get("type") in ["National holiday", "Religious holiday"]:
                return holiday.get("name")
        
        # If no major holiday, return the first one found (could be a local observance)
        return holidays[0].get("name")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching festival data from API: {e}")
        return None # Return None if the API call fails
    except Exception as e:
        print(f"An unexpected error occurred in get_indian_festival_today: {e}")
        return None


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
        print(f"Briefing weather error for city {city}: {e}")
        return None
