# services.py

import requests
import os
from datetime import datetime
import random

def get_daily_quote():
    """
    Fetches a random quote from the ZenQuotes API.
    """
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()
        data = response.json()[0]
        return f"\"{data['q']}\" - {data['a']}"
    except Exception as e:
        print(f"Error fetching daily quote: {e}")
        return "\"The best way to predict the future is to create it.\" - Peter Drucker"

# --- MODIFIED AND NEW FUNCTIONS ---

def get_tech_headline():
    """
    Fetches the top tech headline from global sources using NewsAPI.
    """
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return "Tech headline unavailable (API key not set)."

    try:
        # Fetch top headlines from the 'technology' category worldwide
        url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("articles"):
            top_article = data["articles"][0]
            return top_article['title']
        else:
            return "No tech headlines found at the moment."
    except Exception as e:
        print(f"Tech headline error: {e}")
        return "Could not fetch tech headline."

def get_briefing_weather(city="Vijayawada"):
    """
    Fetches a simple weather update for the daily briefing.
    """
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

def get_tech_tip():
    """
    Returns a random tech/coding tip from a predefined list.
    """
    tips = [
        "Use `Ctrl + /` in your code editor to quickly comment or uncomment lines.",
        "The `zip()` function in Python is great for combining two lists into a dictionary.",
        "Always use virtual environments for your Python projects to manage dependencies.",
        "In Git, `git stash` is a lifesaver for saving changes you aren't ready to commit yet.",
        "You can use `console.time()` and `console.timeEnd()` in JavaScript to measure code execution time.",
        "The CSS selector `*` applies styles to all elements. Use it carefully!",
        "In Python, f-strings (`f\"Hello {name}\"`) are the modern and most readable way to format strings.",
        "To prevent your computer from sleeping, you can use the `caffeinate` command on macOS or a simple script on Windows.",
        "`Ctrl + Shift + T` in your browser reopens the last closed tab. It's a game-changer!"
    ]
    return random.choice(tips)
