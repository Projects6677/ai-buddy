# services.py

import requests
import os
from datetime import datetime
import random
from googleapiclient.discovery import build
from grok_ai import summarize_emails_with_grok, get_smart_greeting, get_conversational_weather

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

def get_tech_headline():
    """Fetches the top tech headline from global sources using NewsAPI."""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return "Tech headline unavailable (API key not set)."
    try:
        url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("articles"):
            return data["articles"][0]['title']
        return "No tech headlines found."
    except Exception as e:
        print(f"Tech headline error: {e}")
        return "Could not fetch tech headline."

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

def get_tech_tip():
    """Returns a random tech/coding tip from a predefined list."""
    tips = [
        "Use `Ctrl + /` in your code editor to quickly comment or uncomment lines.",
        "The `zip()` function in Python is great for combining two lists into a dictionary.",
        "Always use virtual environments for your Python projects to manage dependencies.",
        "In Git, `git stash` is a lifesaver for saving changes you aren't ready to commit yet.",
    ]
    return random.choice(tips)

def get_email_summary(credentials):
    """Fetches and summarizes recent emails from the user's Gmail account."""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        query = 'in:inbox newer_than:12h'
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])

        if not messages:
            return None

        email_content_for_summary = ""
        for msg in messages[:3]:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload['headers']
            
            subject = next((d['value'] for d in headers if d['name'] == 'Subject'), 'No Subject')
            sender = next((d['value'] for d in headers if d['name'] == 'From'), 'Unknown Sender')
            
            email_content_for_summary += f"From: {sender}\nSubject: {subject}\nSnippet: {txt['snippet']}\n---\n"

        return summarize_emails_with_grok(email_content_for_summary)

    except Exception as e:
        print(f"Email summary error: {e}")
        return "Could not retrieve email summary."
