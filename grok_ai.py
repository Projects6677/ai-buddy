# grok_ai.py
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL_FAST = "llama3-8b-8192"
GROK_MODEL_SMART = "llama3-70b-8192"
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}


# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing,
    including a culturally-aware greeting.
    """
    if not GROK_API_KEY:
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Have a great day!",
            "detailed_history": "No historical fact found for today.",
            "detailed_weather": "Weather data is currently unavailable."
        }

    history_texts = [event.get("text", "") for event in history_events]
    
    prompt = f"""
    You are an expert AI assistant with a deep understanding of Indian culture. Your persona is that of a helpful Indian friend creating an engaging daily briefing.
    Today's date is {datetime.now().strftime('%A, %B %d, %Y')}. The user's name is {user_name}.

    You must generate four distinct pieces of content based on the data provided below and return them in a single JSON object with the keys: "greeting", "quote_explanation", "detailed_history", and "detailed_weather".

    1.  **Greeting Generation:**
        -   Today's known festival is: "{festival_name if festival_name else 'None'}".
        -   Task: Create a cheerful morning greeting.
        -   **Strict Rules:** If a festival_name is provided (e.g., "Raksha Bandhan"), you MUST generate a festive greeting for it. If festival_name is "None", you MUST generate a standard "Good Morning" greeting.
        -   Example (if festival is "Raksha Bandhan"): "Happy Raksha Bandhan, {user_name}!"
        -   Example (if festival is "None"): "☀️ Good Morning, {user_name}!"

    2.  **Quote Analysis:**
        -   Quote: "{quote}" by {author}
        -   Task: Explain the meaning of this quote in one insightful sentence.

    3.  **Historical Event:**
        -   Events: {json.dumps(history_texts)}
        -   Task: Pick the most interesting event from the list and write an engaging 2-3 sentence summary about it.

    4.  **Weather Forecast:**
        -   Weather Data: {json.dumps(weather_data)}
        -   Task: Write a friendly, detailed weather forecast for Vijayawada. Mention temperature, conditions, and a helpful suggestion.

    Return only the JSON object.
    """

    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok unified briefing error: {e}")
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Could not generate explanation.",
            "detailed_history": "Could not generate historical fact.",
            "detailed_weather": "Could not generate weather forecast."
        }


# --- PRIMARY INTENT ROUTER ---
def route_user_intent(text):
    if not GROK_API_KEY:
        return {"intent": "general_query", "entities": {}}

    prompt = f"""
    You are an expert AI routing system for a WhatsApp assistant. Your job is to analyze the user's text and classify it into one of the predefined intents.
    You MUST respond with a JSON object containing two keys: "intent" and "entities".

    The current date is: {datetime.now().strftime('%Y-%m-%d %A, %H:%M:%S')}

    Here are the possible intents and the required entities for each:

    1. "schedule_meeting":
       - Triggered by requests to schedule a meeting, find a time, or set up a call with others.
       - "entities": {{"attendees": ["list_of_names"], "topic": "meeting_subject", "duration_minutes": <number>, "timeframe_hint": "e.g., 'next week', 'tomorrow afternoon', 'this Friday'"}}

    2. "set_reminder":
       - Triggered by requests to be reminded of something (for the user only).
       - "entities": An ARRAY of objects, each with {{"task": "The core task of the reminder, e.g., 'call John'", "timestamp": "The fully resolved date and time for the reminder in 'YYYY-MM-DD HH:MM:SS' format.", "recurrence": "The recurrence rule if mentioned (e.g., 'every day'), otherwise null"}}

    3. "get_reminders":
       - Triggered by requests to see, check, show, or list all active reminders.
       - "entities": {{}}

    4. "log_expense":
       - "entities": An array of objects, each with {{"cost": <number>, "item": "description", "place": "store_name_or_null", "timestamp": "YYYY-MM-DD HH:MM:SS format"}}

    5. "convert_currency":
       - "entities": An array of objects, each with {{"amount": <number>, "from_currency": "3-letter_code", "to_currency": "3-letter_code"}}

    6. "get_weather":
       - "entities": {{"location": "city_name"}}

    7. "get_features":
       - Triggered by questions like "what can you do?", "what are your features?", "help", or "what are your commands?".
       - "entities": {{}}

    8. "get_bot_identity":
       - Triggered by questions like "who are you?", "what are you?", "who made you?", or "who created you?".
       - "entities": {{}}

    9. "youtube_search":
       - Triggered by requests to find, search for, or get a video from YouTube.
       - "entities": {{"query": "The search term for the video."}}

    10. "drive_search_file":
        - Triggered by requests to find or search for a file in Google Drive.
        - "entities": {{"query": "The name or keyword of the file to search for."}}

    11. "drive_analyze_file":
        - Triggered by requests to summarize, analyze, or ask questions about a specific file in Google Drive.
        - "entities": {{"filename": "The exact or partial filename to analyze."}}

    12. "general_query":
        - This is the default intent for any other general question or command.
        - "entities": {{}}

    ---
    User's text to analyze: "{text}"
    ---

    Return only the JSON object.
    """
    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok intent routing error: {e}")
        return {"intent": "general_query", "entities": {}}


# --- OTHER AI FUNCTIONS ---
# ... (The rest of the grok_ai.py file remains the same) ...
