# grok_ai.py
import requests
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL_FAST = "llama3-8b-8192"
GROK_MODEL_SMART = "llama3-70b-8192"
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

def _grok_api_call(model, messages, temperature=0.7, timeout=30, response_format=None):
    """A helper function to centralize all Grok API calls."""
    if not GROK_API_KEY:
        return None
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    if response_format:
        payload["response_format"] = response_format
        
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error from Grok API: {e.response.text}")
    except Exception as e:
        logger.error(f"Grok API call error: {e}")
    return None


# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing,
    including a culturally-aware greeting.
    """
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
    
    messages = [{"role": "user", "content": prompt}]
    result_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.7, timeout=45, response_format={"type": "json_object"})
    
    if result_text:
        try:
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for daily briefing: {e}")

    # Fallback to non-AI generated content if API call fails
    return {
        "greeting": f"☀️ Good Morning, {user_name}!",
        "quote_explanation": f"The quote '{quote}' by {author} suggests that our actions shape our character just as we choose our actions.",
        "detailed_history": history_events[0].get('text', "No historical fact found for today."),
        "detailed_weather": f"The weather in Vijayawada is currently {weather_data.get('main', {}).get('temp', 'N/A')}°C with {weather_data.get('weather', [{}])[0].get('description', 'N/A')}."
    }


# --- PRIMARY INTENT ROUTER ---
def route_user_intent(text):
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
    messages = [{"role": "user", "content": prompt}]
    result_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.0, timeout=45, response_format={"type": "json_object"})
    
    if result_text:
        try:
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for intent router: {e}")

    return {"intent": "general_query", "entities": {}}


# --- NEW WEATHER SUMMARY FUNCTION ---
def generate_weather_summary(weather_data, location):
    """
    Uses AI to create a conversational weather summary from raw API data.
    """
    # Provide a basic fallback if AI is not available
    if not GROK_API_KEY:
        temp = weather_data.get('main', {}).get('temp', 'N/A')
        condition = weather_data.get('weather', [{}])[0].get('description', 'N/A')
        return f"🌤️ The weather in {location} is currently {temp}°C with {condition}."

    prompt = f"""
    You are a friendly and helpful weather reporter. Based on the following raw weather data for {location}, write a detailed and engaging 2-3 sentence summary.

    - Main condition: {weather_data.get('weather', [{}])[0].get('description', 'N/A')}
    - Temperature: {weather_data.get('main', {}).get('temp', 'N/A')}°C
    - Feels like: {weather_data.get('main', {}).get('feels_like', 'N/A')}°C
    - Humidity: {weather_data.get('main', {}).get('humidity', 'N/A')}%
    - Wind speed: {weather_data.get('wind', {}).get('speed', 'N/A')} m/s

    Start with an emoji that matches the weather. Be conversational and give a helpful tip (e.g., "it's a good day for a walk," or "you might want to carry an umbrella").
    """
    messages = [{"role": "user", "content": prompt}]
    summary = _grok_api_call(GROK_MODEL_FAST, messages, temperature=0.7, timeout=20)
    
    if summary:
        return summary
    
    temp = weather_data.get('main', {}).get('temp', 'N/A')
    condition = weather_data.get('weather', [{}])[0].get('description', 'N/A')
    return f"🌤️ The weather in {location} is currently {temp}°C with {condition}."


# --- OTHER AI FUNCTIONS ---
def analyze_document_context(text):
    if not text or not text.strip(): return None
    prompt = f"""You are an expert document analysis AI. Read the following text and determine its type and extract key information. Your response MUST be a JSON object with two keys: "doc_type" and "data". Possible "doc_type" values are: "resume", "project_plan", "meeting_invite", "q_and_a", "generic_document". The "data" key should be an empty object `{{}}` unless it's a "meeting_invite", in which case it should be `{{"task": "description of event", "timestamp": "YYYY-MM-DD HH:MM:SS"}}`. The current date is {datetime.now().strftime('%Y-%m-%d %A')}. Here is the text to analyze: --- {text} --- Return only the JSON object."""
    messages = [{"role": "user", "content": prompt}]
    result_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.1, timeout=45, response_format={"type": "json_object"})
    
    if result_text:
        try:
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for document analysis: {e}")
            
    return None

def get_contextual_ai_response(document_text, question):
    prompt = f"""You are an AI assistant with a document's content loaded into your memory. A user is now asking a question about this document. Your task is to answer their question based *only* on the information provided in the document text. Here is the full text of the document: --- DOCUMENT START --- {document_text} --- DOCUMENT END --- Here is the user's question: "{question}". Provide a direct and helpful answer. If the answer cannot be found in the document, say "I couldn't find the answer to that in the document." """
    messages = [{"role": "user", "content": prompt}]
    response_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.3, timeout=60)
    
    return response_text.strip() if response_text else "⚠️ Sorry, I had trouble answering that question."

def is_document_followup_question(text):
    command_keywords = ["remind me", "hi", "hello", "hey", "menu", "what's the weather", "convert", "translate", "fix grammar", "my expenses", "send an email", ".dev", ".test", ".nuke", ".stats"]
    if any(keyword in text.lower() for keyword in command_keywords):
        return False
    prompt = f"""A user has previously uploaded a document and is in a follow-up conversation. Their new message is: "{text}". Is this message a question or command related to the document (e.g., "summarize it", "what are the key points?")? Or is it a completely new, unrelated command? Respond with only the word "yes" if it is a follow-up, or "no" if it is a new command."""
    messages = [{"role": "user", "content": prompt}]
    response_text = _grok_api_call(GROK_MODEL_FAST, messages, temperature=0.0, timeout=10)
    
    return "yes" in response_text.strip().lower() if response_text else True

def ai_reply(prompt):
    messages = [{"role": "user", "content": prompt}]
    response_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.7, timeout=20)
    
    return response_text.strip() if response_text else "⚠️ Sorry, I couldn't connect to the AI service right now."

def correct_grammar_with_grok(text):
    system_prompt = "You are an expert grammar and spelling correction assistant. Correct the user's text. Only return the corrected text, without any explanation or preamble."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
    corrected_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.2, timeout=20)
    
    if corrected_text:
        return f"✅ Corrected:\n\n_{corrected_text.strip().strip('"')}_"
    else:
        return "⚠️ Sorry, the grammar correction service is unavailable."

def analyze_email_subject(subject):
    prompt = f"""You are an email assistant. The user wants to write an email with the subject: "{subject}". What are the 2-3 most important follow-up questions you should ask to get the necessary details to write this email? Return your answer as a JSON object with a single key "questions" which is an array of strings. For a 'leave' subject, ask for dates and reason. For a 'meeting request' subject, ask for topic, date/time, and attendees. For a generic subject, just ask for the main point of the email. Only return the JSON object."""
    messages = [{"role": "user", "content": prompt}]
    result_text = _grok_api_call(GROK_MODEL_FAST, messages, temperature=0.2, timeout=15, response_format={"type": "json_object"})
    
    if result_text:
        try:
            return json.loads(result_text).get("questions")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for email subject analysis: {e}")
    return None

def write_email_body_with_grok(prompt):
    system_prompt = "You are an expert email writing assistant. Based on the user's prompt, write a clear, professional, and well-formatted email body. Your entire response must consist *only* of the email body text. Do not include a subject line, greetings like 'Hello,', sign-offs like 'Sincerely,', or any preamble like 'Here is the email body:'."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.7, timeout=30)
    
    return response_text.strip() if response_text else "❌ Sorry, I couldn't write the email body right now."

def edit_email_body(original_draft, edit_instruction):
    prompt = f"""You are an email editor. Here is an email draft: --- DRAFT --- {original_draft} --- END DRAFT --- The user wants to make a change. Their instruction is: "{edit_instruction}". Apply the change and return only the complete, new version of the email body."""
    messages = [{"role": "user", "content": prompt}]
    response_text = _grok_api_call(GROK_MODEL_SMART, messages, temperature=0.5, timeout=30)
    
    return response_text.strip() if response_text else None
