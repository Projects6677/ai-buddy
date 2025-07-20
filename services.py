# services.py

import requests
from datetime import datetime
import random

def get_daily_quote():
    """
    Fetches a random quote from the ZenQuotes API.
    This API requires no key.
    """
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()[0]
        # 'q' is the quote, 'a' is the author
        return f"\"{data['q']}\" - {data['a']}"
    except Exception as e:
        print(f"Error fetching daily quote: {e}")
        # Return a reliable fallback quote if the API fails
        return "\"The best way to predict the future is to create it.\" - Peter Drucker"

def get_on_this_day_facts():
    """
    Fetches 'On This Day' historical facts from the Wikimedia Feed API.
    This API is free and requires no key.
    """
    try:
        today = datetime.now()
        month = today.strftime('%m')
        day = today.strftime('%d')
        
        # API Documentation: https://api.wikimedia.org/wiki/Feed_API/Reference/On_this_day
        url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/{month}/{day}"
        
        # It's good practice to set a User-Agent header for public APIs
        headers = {'User-Agent': 'AI-Buddy-WhatsApp-Bot/1.0 (https://your-contact-page-or-github)'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Get up to 3 random events to keep the message from being too long
        if "events" in data and len(data["events"]) > 0:
            num_events = min(len(data["events"]), 3)
            # random.sample ensures we get unique events
            selected_events = random.sample(data["events"], k=num_events)
            
            fact_strings = [f"• In {event['year']}, {event['text']}" for event in selected_events]
            return "\n".join(fact_strings)
        else:
            return "No historical facts found for today."
            
    except Exception as e:
        print(f"Error fetching 'On This Day' facts: {e}")
        return "Could not retrieve historical facts today."
