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


# --- NEW: ENHANCED BRIEFING GENERATOR ---
def generate_enhanced_briefing(quote, author, history_events, weather_data):
    """
    Uses a single AI call to generate detailed explanations for the daily briefing.
    """
    if not GROK_API_KEY:
        return {
            "quote_explanation": "Have a great day!",
            "detailed_history": "No historical fact found for today.",
            "detailed_weather": "Weather data is currently unavailable."
        }

    history_texts = [event.get("text", "") for event in history_events]
    
    prompt = f"""
    You are an expert AI assistant that creates engaging daily briefing content.
    The current user is in Vijayawada, India.
    Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.

    You must generate three distinct pieces of content based on the data provided below and return them in a single JSON object with the keys: "quote_explanation", "detailed_history", and "detailed_weather".

    1.  **Quote Analysis:**
        -   Quote: "{quote}"
        -   Author: {author}
        -   Task: Explain the meaning and relevance of this quote in a single, insightful sentence.

    2.  **Historical Event:**
        -   Events: {json.dumps(history_texts)}
        -   Task: From the list of historical events, pick the most interesting one and write a slightly more detailed and engaging summary about it (2-3 sentences).

    3.  **Weather Forecast:**
        -   Weather Data: {json.dumps(weather_data)}
        -   Task: Write a friendly, conversational, and more detailed weather forecast for Vijayawada. Mention the current temperature, what it feels like, the conditions (e.g., "sunny with scattered clouds"), and the wind speed. Add a brief suggestion, like what to wear or if it's a good day to be outside.

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
        print(f"Grok enhanced briefing error: {e}")
        return {
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

    The current date is: {datetime.now().strftime('%Y-%m-%d %A')}

    Here are the possible intents and the required entities for each:

    1. "set_reminder":
       - Triggered by requests to be reminded of something.
       - "entities": {{"task": "The thing to be reminded of", "timestamp": "The exact time in YYYY-MM-DD HH:MM:SS format"}}

    2. "log_expense":
       - Triggered by statements about spending money.
       - "entities": An array of objects, each with {{"cost": <number>, "item": "description", "place": "store_name_or_null", "timestamp": "YYYY-MM-DD_or_null"}}

    3. "convert_currency":
       - Triggered by requests to convert currencies.
       - "entities": An array of objects, each with {{"amount": <number>, "from_currency": "3-letter_code", "to_currency": "3-letter_code"}}

    4. "get_weather":
       - Triggered by requests for weather information.
       - "entities": {{"location": "city_name"}}

    5. "export_expenses":
       - Triggered by requests to export, download, or get an expense report, sheet, or excel file.
       - "entities": {{}}

    6. "general_query":
       - This is the default intent for any general question, statement, or command that doesn't fit the other categories.
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
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=25)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok intent routing error: {e}")
        return {"intent": "general_query", "entities": {}}


# --- OTHER AI FUNCTIONS ---
def get_smart_greeting(user_name):
    if not GROK_API_KEY: return f"☀️ Good Morning, {user_name}!"
    prompt = f"You are an AI assistant that writes cheerful morning greetings for a user named {user_name}. Today's date is {datetime.now().strftime('%A, %B %d, %Y')}. Check if today is a well-known special day (e.g., a holiday like Diwali, Friendship Day, International Cat Day, etc.). If it IS a special day, create a short, festive greeting like '🎉 Happy Friendship Day, {user_name}!'. If it is NOT a special day, just return a standard greeting like '☀️ Good Morning, {user_name}!'. Return only the greeting text."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok smart greeting error: {e}")
        return f"☀️ Good Morning, {user_name}!"

def analyze_document_context(text):
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

def get_contextual_ai_response(document_text, question):
    if not GROK_API_KEY: return "❌ The Grok API key is not configured."
    prompt = f"""You are an AI assistant with a document's content loaded into your memory. A user is now asking a question about this document. Your task is to answer their question based *only* on the information provided in the document text. Here is the full text of the document: --- DOCUMENT START --- {document_text} --- DOCUMENT END --- Here is the user's question: "{question}". Provide a direct and helpful answer. If the answer cannot be found in the document, say "I couldn't find the answer to that in the document." """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok contextual response error: {e}")
        return "⚠️ Sorry, I had trouble answering that question."

def is_document_followup_question(text):
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

def ai_reply(prompt):
    if not GROK_API_KEY: return "❌ The Grok API key is not configured. This feature is disabled."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok AI error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now."

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

def translate_with_grok(text):
    if not GROK_API_KEY: return "❌ The Grok API key is not configured. This feature is disabled."
    system_prompt = "You are a translation assistant. The user will provide text to be translated, and they will specify the target language. Your task is to provide the translation. Only return the translated text."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        translated_text = response.json()["choices"][0]["message"]["content"].strip()
        return f"🌍 Translated:\n\n_{translated_text}_"
    except Exception as e:
        print(f"Grok Translation error: {e}")
        return "⚠️ Sorry, the translation service is currently unavailable."
