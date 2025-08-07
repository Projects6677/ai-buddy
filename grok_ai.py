# grok_ai.py
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
# --- MODIFICATION START ---
# Updated to use the latest GPT-OSS models
GROK_MODEL_FAST = "openai/gpt-oss-20b"
GROK_MODEL_SMART = "openai/gpt-oss-120b"
# --- MODIFICATION END ---
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# --- CONVERSATIONAL AI FUNCTIONS ---

def get_smart_greeting(user_name):
    """Generates a smart, context-aware greeting for the daily briefing."""
    if not GROK_API_KEY: return f"☀️ Good Morning, {user_name}!"

    prompt = f"""
    You are an AI assistant that writes cheerful morning greetings.
    Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.
    Check if today is a well-known special day (e.g., a holiday like Diwali, Friendship Day, etc.).

    - If it IS a special day, create a short, festive greeting. For example: "🎉 Happy Friendship Day, {user_name}!"
    - If it is NOT a special day, just return the standard greeting: "☀️ Good Morning, {user_name}!"

    Return only the greeting text.
    """
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

    # Step 1: Get raw weather data
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

    # Step 2: Use AI to make it conversational
    prompt = f"""
    You are an AI weather forecaster. Given the following weather data, write a short, friendly, and conversational forecast (1-2 sentences).
    If it's raining or cloudy, suggest taking an umbrella. If it's sunny, suggest it's a nice day to be outside.

    - Location: {city}
    - Temperature: {temp}°C
    - Conditions: {weather_description}

    Example: "It looks like a clear day in Vijayawada with a temperature of around 30°C. Perfect weather to be outside!"
    Return only the forecast text.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok conversational weather error: {e}")
        return f"Today in {city}: {temp}°C, {weather_description}."
        
def analyze_document_context(text):
    """
    Analyzes document text to understand its type and extract key data for follow-up actions.
    """
    if not GROK_API_KEY: return None
    if not text or not text.strip(): return None

    prompt = f"""
    You are an expert document analysis AI. Read the following text and determine its type and extract key information.
    Your response MUST be a JSON object with two keys: "doc_type" and "data".

    Possible "doc_type" values are:
    1. "resume": For a professional resume or CV.
    2. "project_plan": For a document outlining a project, idea, or business plan.
    3. "meeting_invite": If the text is an invitation with a clear task and time.
    4. "q_and_a": If the document is primarily a list of questions.
    5. "generic_document": For articles, notes, or anything else.

    The "data" key should be an empty object `{{}}` unless it's a "meeting_invite", in which case it should be:
    `{{"task": "description of event", "timestamp": "YYYY-MM-DD HH:MM:SS"}}`

    The current date is {datetime.now().strftime('%Y-%m-%d %A')}.

    Here is the text to analyze:
    ---
    {text}
    ---

    Return only the JSON object.
    """
    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok document context analysis error: {e}")
        return None

def get_contextual_ai_response(document_text, question):
    """
    Answers a user's question based on the context of a previously uploaded document.
    """
    if not GROK_API_KEY: return "❌ The Grok API key is not configured."

    prompt = f"""
    You are an AI assistant with a document's content loaded into your memory.
    A user is now asking a question about this document. Your task is to answer their question based *only* on the information provided in the document text.

    Here is the full text of the document:
    --- DOCUMENT START ---
    {document_text}
    --- DOCUMENT END ---

    Here is the user's question:
    "{question}"

    Provide a direct and helpful answer. If the answer cannot be found in the document, say "I couldn't find the answer to that in the document."
    """
    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok contextual response error: {e}")
        return "⚠️ Sorry, I had trouble answering that question."

def is_document_followup_question(text):
    """
    Quickly determines if a user's message is a follow-up question or a new command.
    """
    if not GROK_API_KEY: return True

    command_keywords = ["remind me", "hi", "hello", "hey", "menu", "what's the weather", "convert", "translate", "fix grammar", "my expenses", "send an email", ".dev", ".test", ".nuke", ".stats"]
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in command_keywords):
        return False

    prompt = f"""
    A user has previously uploaded a document and is in a follow-up conversation.
    Their new message is: "{text}"
    Is this message a question or command related to the.document (e.g., "summarize it", "what are the key points?", "critique it")?
    Or is it a completely new, unrelated command (e.g., a greeting, a reminder request, a weather query)?
    Respond with only the word "yes" if it is a follow-up, or "no" if it is a new command.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip().lower()
        return "yes" in reply
    except Exception as e:
        print(f"Grok context check error: {e}")
        return True

# (The rest of your functions: is_expense_intent, ai_reply, etc. remain the same)
def is_expense_intent(text):
    if not GROK_API_KEY: return False
    prompt = f"""
    You are an intent classification assistant. Read the text and determine if the user is trying to log a financial expense.
    An expense includes words about buying, spending, or acquiring something with a cost.
    The text is: "{text}"
    Respond with only the word "yes" or "no".
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip().lower()
        return "yes" in reply
    except Exception as e:
        print(f"Grok intent classification error: {e}")
        return False

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
    system_prompt = """
    You are an expert grammar and spelling correction assistant. Correct the user's text.
    If the text is heavily misspelled or jumbled, interpret the user's likely intent and provide the most logical, natural-sounding correction.
    Only return the corrected text, without any explanation, preamble, or quotation marks.
    For example, if the user says 'herrr are you', the likely intent is 'How are you?'.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.2 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        corrected_text = res.json()["choices"][0]["message"]["content"].strip()
        if corrected_text.startswith('"') and corrected_text.endswith('"'):
            corrected_text = corrected_text[1:-1]
        return f"✅ Corrected:\n\n_{corrected_text}_"
    except Exception as e:
        print(f"Grok Grammar error: {e}")
        return "⚠️ Sorry, the grammar correction service is unavailable."

def parse_expense_with_grok(text):
    if not GROK_API_KEY: return None
    prompt = f"""
    You are an expert expense parsing assistant. Your task is to extract all expenses from the user's text.
    The current date is {datetime.now().strftime('%Y-%m-%d')}.
    The text is: "{text}"
    Extract the cost (as a number), the item purchased, the place of purchase (if mentioned), and the timestamp (if mentioned, like "yesterday" or "July 17th").
    Return the result as a JSON object with a single key "expenses" which is an array of objects.
    Each object must have keys "cost", "item", "place", and "timestamp".
    If a place or timestamp is not mentioned, set its value to null.
    Only return the JSON object.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("expenses")
    except Exception as e:
        print(f"Grok expense parsing error: {e}")
        return None

def parse_reminder_with_grok(text):
    if not GROK_API_KEY: return None, None
    prompt = f"""
    You are a task and time extraction assistant. From the user's text, identify the core task and the specific timestamp.
    The current date is {datetime.now().strftime('%Y-%m-%d %A')}.
    The user's text is: "{text}"
    Return a JSON object with two keys: "task" (the what) and "timestamp" (the when).
    The timestamp should be in a machine-readable format like 'YYYY-MM-DD HH:MM:SS'.
    Only return the JSON object.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("task"), result_data.get("timestamp")
    except Exception as e:
        print(f"Grok reminder parsing error: {e}")
        return None, None

def parse_currency_with_grok(text):
    if not GROK_API_KEY: return None
    prompt = f"""
    You are an expert currency conversion parser. From the user's text, extract all requests to convert money.
    The user's text is: "{text}"
    Return a JSON object with a single key "conversions" which is an array of objects.
    Each object must have keys "amount", "from_currency", and "to_currency".
    Use standard 3-letter currency codes (e.g., USD, INR, EUR).
    Only return the JSON object.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("conversions")
    except Exception as e:
        print(f"Grok currency parsing error: {e}")
        return None

def summarize_emails_with_grok(email_text):
    if not GROK_API_KEY: return None
    if not email_text.strip(): return None

    prompt = f"""
    You are an expert at summarizing emails into a neat, bulleted list.
    Read the following email content and provide a very short, clean summary of the key points.
    Each point must start with a hyphen (-).
    Focus on the sender and the main topic.
    If there is nothing important or no content, return the single phrase "No important updates."

    Email Content:
    ---
    {email_text}
    ---

    Return only the summary.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"].strip()
        if "no important updates" in summary.lower():
            return None
        return summary
    except Exception as e:
        print(f"Grok email summarization error: {e}")
        return None

def analyze_email_subject(subject):
    if not GROK_API_KEY: return None
    prompt = f"""
    You are an email assistant. The user wants to write an email with the subject: "{subject}".
    What are the 2-3 most important follow-up questions you should ask to get the necessary details to write this email?
    Return your answer as a JSON object with a single key "questions" which is an array of strings.
    For a 'leave' subject, ask for dates and reason. For a 'meeting request' subject, ask for topic, date/time, and attendees.
    For a generic subject, just ask for the main point of the email.
    Only return the JSON object.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("questions")
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
    prompt = f"""
    You are an email editor. Here is an email draft:
    --- DRAFT ---
    {original_draft}
    --- END DRAFT ---

    The user wants to make a change. Their instruction is: "{edit_instruction}"

    Apply the change and return only the complete, new version of the email body.
    Do not add any preamble, explanation, or quotation marks.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok email editing error: {e}")
        return None

def translate_with_grok(text):
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured. This feature is disabled."
    
    system_prompt = "You are a translation assistant. The user will provide text to be translated, and they will specify the target language. Your task is to provide the translation. Only return the translated text, without any additional comments or explanations."
    
    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        translated_text = response.json()["choices"][0]["message"]["content"].strip()
        return f"🌍 Translated:\n\n_{translated_text}_"
    except Exception as e:
        print(f"Grok Translation error: {e}")
        return "⚠️ Sorry, the translation service is currently unavailable."
