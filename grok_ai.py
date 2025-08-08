# grok_ai.py
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL_FAST = "openai/gpt-oss-20b"
GROK_MODEL_SMART = "openai/gpt-oss-120b"
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# --- NEW: PRIMARY INTENT ROUTER ---
def route_user_intent(text):
    """
    Analyzes user text to determine intent and extract entities in a single API call.
    """
    if not GROK_API_KEY:
        # Fallback for when API key is not available
        return {"intent": "general_query", "entities": {}}

    # The current date is provided for context, helping the AI parse relative dates like "tomorrow"
    prompt = f"""
    You are an expert AI routing system for a WhatsApp assistant. Your job is to analyze the user's text and classify it into one of the predefined intents.
    You MUST respond with a JSON object containing two keys: "intent" and "entities".

    The current date is: {datetime.now().strftime('%Y-%m-%d %A')}

    Here are the possible intents and the required entities for each:

    1. "set_reminder":
       - Triggered by requests to be reminded of something.
       - "entities": {{"task": "The thing to be reminded of", "timestamp": "The exact time in YYYY-MM-DD HH:MM:SS format"}}
       - Example: "remind me to call the doctor tomorrow at 4pm" -> {{"intent": "set_reminder", "entities": {{"task": "call the doctor", "timestamp": "YYYY-MM-DD 16:00:00"}}}}

    2. "log_expense":
       - Triggered by statements about spending money.
       - "entities": An array of objects, each with {{"cost": <number>, "item": "description", "place": "store_name_or_null", "timestamp": "YYYY-MM-DD_or_null"}}
       - Example: "spent 500 on groceries at d-mart" -> {{"intent": "log_expense", "entities": [{{"cost": 500, "item": "groceries", "place": "d-mart", "timestamp": null}}]}}
       - Example: "i spent 100rs at canteen today for lunch" -> {{"intent": "log_expense", "entities": [{{"cost": 100, "item": "lunch", "place": "canteen", "timestamp": "YYYY-MM-DD"}}]}}

    3. "convert_currency":
       - Triggered by requests to convert currencies.
       - "entities": An array of objects, each with {{"amount": <number>, "from_currency": "3-letter_code", "to_currency": "3-letter_code"}}
       - Example: "how much is 100 usd in inr" -> {{"intent": "convert_currency", "entities": [{{"amount": 100, "from_currency": "USD", "to_currency": "INR"}}]}}

    4. "get_weather":
       - Triggered by requests for weather information.
       - "entities": {{"location": "city_name"}}
       - Example: "what's the weather like in hyderabad" -> {{"intent": "get_weather", "entities": {{"location": "hyderabad"}}}}

    5. "general_query":
       - This is the default intent for any general question, statement, or command that doesn't fit the other categories.
       - "entities": {{}}
       - Example: "who was the first prime minister of india?" -> {{"intent": "general_query", "entities": {{}}}}

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
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=25)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok intent routing error: {e}")
        # Fallback to general query if routing fails
        return {"intent": "general_query", "entities": {}}


# --- CONVERSATIONAL AI FUNCTIONS (These have been updated to handle memory) ---

def get_chat_response(prompt, chat_history=[], document_text=None):
    """
    Handles a conversational chat, using previous history and optional document context.
    """
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured.", []
    
    # Start with a clean list of messages
    messages = []
    
    # Add a system prompt to define the AI's role.
    system_prompt_content = "You are an AI assistant. Be friendly, helpful, and concise. Respond in a natural, conversational tone."
    
    # If document text is available, add a special instruction to the system prompt.
    if document_text:
        system_prompt_content += f"\n\n--- CONTEXT DOCUMENT ---\n{document_text}\n--- END CONTEXT ---\n\nAnswer all questions based on the provided document. If you cannot find the answer in the document, say 'I couldn't find that information in the document.' Do not use any outside knowledge."
    
    messages.append({"role": "system", "content": system_prompt_content})
    
    # Add the existing chat history
    messages.extend(chat_history)
    
    # Add the current user prompt
    messages.append({"role": "user", "content": prompt})

    payload = { 
        "model": GROK_MODEL_SMART, 
        "messages": messages, 
        "temperature": 0.7 
    }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        ai_response_content = res.json()["choices"][0]["message"]["content"].strip()
        
        # Append both the user's message and the AI's response to the history for the next turn
        updated_history = chat_history + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": ai_response_content}
        ]
        
        return ai_response_content, updated_history

    except Exception as e:
        print(f"Grok AI error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now.", chat_history

# --- OTHER FUNCTIONS (These remain unchanged) ---

def get_smart_greeting(user_name):
    """Generates a smart, context-aware greeting for the daily briefing."""
    if not GROK_API_KEY: return f"☀️ Good Morning, {user_name}!"
    prompt = f"You are an AI assistant that writes cheerful morning greetings. Today's date is {datetime.now().strftime('%A, %B %d, %Y')}. Check if today is a well-known special day (e.g., a holiday like Diwali, Friendship Day, etc.). If it IS a special day, create a short, festive greeting like '🎉 Happy Friendship Day, {user_name}!'. If it is NOT a special day, just return the standard greeting: '☀️ Good Morning, {user_name}!'. Return only the greeting text."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok smart greeting error: {e}")
        return f"☀️ Good Morning, {user_name}!"

def get_conversational_weather(city="Vijayawada"):
    """Gets weather data and uses AI to create a conversational forecast."""
    if not GROK_API_KEY or not os.environ.get("OPENWEATHER_API_KEY"):
        return "Weather data is currently unavailable."
    try:
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        weather_description = data['weather'][0]['description']
        temp = data['main']['temp']
    except Exception as e:
        print(f"Raw weather fetch error: {e}")
        return "Could not fetch today's weather data."
    prompt = f"You are an AI weather forecaster. Given the following weather data, write a short, friendly, and conversational forecast (1-2 sentences). If it's raining or cloudy, suggest taking an umbrella. If it's sunny, suggest it's a nice day to be outside. Location: {city}, Temperature: {temp}°C, Conditions: {weather_description}. Example: 'It looks like a clear day in Vijayawada with a temperature of around 30°C. Perfect weather to be outside!'. Return only the forecast text."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok conversational weather error: {e}")
        return f"Today in {city}: {temp}°C, {weather_description}."

def analyze_document_context(text):
    """Analyzes document text to understand its type and extract key data for follow-up actions."""
    if not GROK_API_KEY or not text or not text.strip(): return None
    prompt = f"""You are an expert document analysis AI. Read the following text and determine its type and extract key information. Your response MUST be a JSON object with two keys: "doc_type" and "data". Possible "doc_type" values are: "resume", "project_plan", "meeting_invite", "q_and_a", "generic_document". The "data" key should be an empty object `{{}}` unless it's a "meeting_invite", in which case it should be `{{"task": "description of event", "timestamp": "YYYY-MM-DD HH:MM:SS"}}`. The current date is {datetime.now().strftime('%Y-%m-%d %A')}. Here is the text to analyze: --- {text} --- Return only the JSON object."""
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Grok document context analysis error: {e}")
        return None

def is_document_followup_question(text):
    """Quickly determines if a user's message is a follow-up question or a new command."""
    if not GROK_API_KEY: return True
    command_keywords = ["remind me", "hi", "hello", "hey", "menu", "what's the weather", "convert", "translate", "fix grammar", "my expenses", "send an email", ".dev", ".test", ".nuke", ".stats"]
    if any(keyword in text.lower() for keyword in command_keywords):
        return False
    prompt = f"""A user has previously uploaded a document and is in a follow-up conversation. Their new message is: "{text}". Is this message a question or command related to the document (e.g., "summarize it", "what are the key points?")? Or is it a completely new, unrelated command? Respond with only the word "yes" if it is a follow-up, or "no" if it is a new command."""
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return "yes" in response.json()["choices"][0]["message"]["content"].strip().lower()
    except Exception as e:
        print(f"Grok context check error: {e}")
        return True

def correct_grammar_with_grok(text):
    if not GROK_API_KEY: return "❌ The Grok API key is not configured. This feature is disabled."
    system_prompt = "You are an expert grammar and spelling correction assistant. Correct the user's text. Only return the corrected text, without any explanation or preamble."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.2 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        corrected_text = res.json()["choices"][0]["message"]["content"].strip().strip('"')
        return f"✅ Corrected:\n\n_{corrected_text}_"
    except Exception as e:
        print(f"Grok Grammar error: {e}")
        return "⚠️ Sorry, the grammar correction service is unavailable."

def analyze_email_subject(subject):
    if not GROK_API_KEY: return None
    prompt = f"""You are an email assistant. The user wants to write an email with the subject: "{subject}". What are the 2-3 most important follow-up questions you should ask to get the necessary details to write this email? Return your answer as a JSON object with a single key "questions" which is an array of strings. For a 'leave' subject, ask for dates and reason. For a 'meeting request' subject, ask for topic, date/time, and attendees. For a generic subject, just ask for the main point of the email. Only return the JSON object."""
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"]).get("questions")
    except Exception as e:
        print(f"Grok subject analysis error: {e}")
        return None

def write_email_body_with_grok(prompt):
    if not GROK_API_KEY: return "❌ The Grok API key is not configured. This feature is disabled."
    system_prompt = "You are an expert email writing assistant. Based on the user's prompt, write a clear, professional, and well-formatted email body. Your entire response must consist *only* of the email body text. Do not include a subject line, greetings like 'Hello,', sign-offs like 'Sincerely,', or any preamble like 'Here is the email body:'."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], "temperature": 0.7 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok email writing error: {e}")
        return "❌ Sorry, I couldn't write the email body right now."

def edit_email_body(original_draft, edit_instruction):
    if not GROK_API_KEY: return None
    prompt = f"""You are an email editor. Here is an email draft: --- DRAFT --- {original_draft} --- END DRAFT --- The user wants to make a change. Their instruction is: "{edit_instruction}". Apply the change and return only the complete, new version of the email body."""
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok email editing error: {e}")
        return None
