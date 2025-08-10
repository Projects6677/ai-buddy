# grok_ai.py
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
# Use official Groq model names for better performance and reliability
GROK_MODEL_FAST = "llama3-8b-8192"    # Fast model for routing and simple tasks
GROK_MODEL_SMART = "llama3-70b-8192"  # Smart model for complex generation and analysis
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}


# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing.
    """
    if not GROK_API_KEY:
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Have a wonderful day!",
            "detailed_history": "Could not retrieve a historical fact for today.",
            "detailed_weather": "Weather data is currently unavailable."
        }

    history_texts = [event.get("text", "") for event in history_events if event]
    
    prompt = f"""
    You are a helpful and culturally aware AI assistant creating a personalized morning briefing for a user in India.
    The user's name is {user_name}. Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.

    Based on the data below, generate a JSON object with four keys: "greeting", "quote_explanation", "detailed_history", and "detailed_weather".

    1.  **Greeting**:
        -   Today's Indian festival: "{festival_name or 'None'}".
        -   Task: Create a cheerful, context-aware greeting. If a festival is named, the greeting MUST be festive. Otherwise, a standard "Good Morning" is perfect.

    2.  **Quote Explanation**:
        -   Quote: "{quote}" by {author}.
        -   Task: Explain the quote's meaning in one insightful sentence.

    3.  **Historical Fact**:
        -   Today's historical events: {json.dumps(history_texts)}
        -   Task: Select the most interesting event and write an engaging 2-3 sentence summary about it.

    4.  **Weather Forecast**:
        -   Raw Weather Data for Vijayawada: {json.dumps(weather_data)}
        -   Task: Provide a friendly, detailed weather forecast. Mention temperature, conditions (e.g., "clear skies"), and a helpful suggestion (e.g., "a great day for a walk").

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
        # Provide a more graceful fallback
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": f"Here is a quote for you: '{quote}' - {author}",
            "detailed_history": "Could not generate a historical fact at this time.",
            "detailed_weather": "Could not retrieve the weather forecast."
        }


# --- PRIMARY INTENT ROUTER ---
def route_user_intent(text):
    """
    Analyzes user text to determine intent and extract entities using a fast AI model.
    """
    if not GROK_API_KEY:
        return {"intent": "general_query", "entities": {}}

    prompt = f"""
    You are an AI routing system for a WhatsApp assistant. Classify the user's text into a predefined intent and extract entities.
    Respond with a JSON object: {{"intent": "...", "entities": {{...}} or [...]}}.
    The current date is: {datetime.now().strftime('%Y-%m-%d %A')}

    Intents & Entities:
    - "set_reminder": For requests to be reminded.
      - entities: ARRAY of {{"task": "...", "time_expression": "...", "recurrence": "..."}}
    - "get_reminders": For requests to list active reminders.
      - entities: {{}}
    - "log_expense": For logging expenses.
      - entities: ARRAY of {{"cost": <number>, "item": "...", "place": "...", "timestamp": "..."}}
    - "convert_currency": For currency conversions.
      - entities: ARRAY of {{"amount": <number>, "from_currency": "...", "to_currency": "..."}}
    - "get_weather": For weather requests.
      - entities: {{"location": "..."}}
    - "export_expenses": For requests to export expense reports.
      - entities: {{}}
    - "general_query": Default for all other questions or commands.
      - entities: {{}}

    ---
    User Text: "{text}"
    ---

    Return only the JSON object.
    """
    payload = {
        "model": GROK_MODEL_SMART, # Smart model is better for complex entity extraction
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


# --- DOCUMENT & CONTEXTUAL AI FUNCTIONS ---
def analyze_document_context(text):
    """Determines a document's type and extracts key information."""
    if not GROK_API_KEY or not text or not text.strip(): return None
    prompt = f"""
    Analyze the text to determine its type and extract key info.
    Respond with JSON: {{"doc_type": "...", "data": {{...}}}}.
    doc_type can be: "resume", "project_plan", "meeting_invite", "q_and_a", "generic_document".
    For "meeting_invite", data should be {{"task": "...", "timestamp": "YYYY-MM-DD HH:MM:SS"}}. Otherwise, data is {{}}.
    Current date: {datetime.now().strftime('%Y-%m-%d %A')}.
    Text: --- {text[:2000]} ---
    Return only the JSON object.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Grok document context analysis error: {e}")
        return None

def get_contextual_ai_response(document_text, question):
    """Answers a question based on the provided document text."""
    if not GROK_API_KEY: return "❌ The AI API key is not configured."
    prompt = f"""
    You are an AI assistant answering a question based ONLY on the document text provided.
    Document: --- {document_text} ---
    Question: "{question}"
    Provide a direct answer. If the answer is not in the document, state that clearly.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok contextual response error: {e}")
        return "⚠️ Sorry, I had trouble answering that question."

def is_document_followup_question(text):
    """Checks if a message is a follow-up question or a new command."""
    if not GROK_API_KEY: return True
    # Keywords for new commands that should immediately break the context loop
    command_keywords = ["remind me", "hi", "hello", "menu", "weather", "convert", "translate", "fix grammar", "my expenses", "send email", ".dev", ".test", ".nuke", ".stats"]
    if any(keyword in text.lower() for keyword in command_keywords):
        return False
        
    prompt = f"""The user previously uploaded a document. Is their new message a follow-up question about it (e.g., "summarize it") or a new, unrelated command?
    Message: "{text}"
    Respond with only "yes" for a follow-up or "no" for a new command.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return "yes" in response.json()["choices"][0]["message"]["content"].strip().lower()
    except Exception as e:
        print(f"Grok context check error: {e}")
        return True # Default to true to be safe and not break context accidentally

# --- GENERAL AI & UTILITY FUNCTIONS ---
def ai_reply(prompt):
    """Gets a general-purpose AI reply."""
    if not GROK_API_KEY: return "❌ The AI API key is not configured."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok AI reply error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now."

def correct_grammar_with_grok(text):
    """Corrects grammar in a given text."""
    if not GROK_API_KEY: return "❌ The AI API key is not configured."
    system_prompt = "You are an expert grammar correction assistant. Correct the user's text and return only the corrected version, without any preamble."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.1 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        corrected_text = res.json()["choices"][0]["message"]["content"].strip().strip('"')
        return f"✅ Corrected:\n\n_{corrected_text}_"
    except Exception as e:
        print(f"Grok Grammar error: {e}")
        return "⚠️ Sorry, the grammar correction service is unavailable."

def analyze_email_subject(subject):
    """Generates follow-up questions for an email subject."""
    if not GROK_API_KEY: return None
    prompt = f"""
    The user wants to write an email with the subject: "{subject}".
    Generate 2-3 key follow-up questions to get the necessary details.
    Return a JSON object with a single key "questions" which is an array of strings.
    Example for 'leave application': ask for dates and reason.
    Example for 'meeting request': ask for topic, date/time, and attendees.
    Return only the JSON object.
    """
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"]).get("questions")
    except Exception as e:
        print(f"Grok subject analysis error: {e}")
        return None

def write_email_body_with_grok(prompt):
    """Writes a professional email body based on a prompt."""
    if not GROK_API_KEY: return "❌ The AI API key is not configured."
    system_prompt = "You are an expert email writing assistant. Write a clear, professional email body based on the user's prompt. Return *only* the email body text, with no subject or sign-off."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], "temperature": 0.7 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=40)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok email writing error: {e}")
        return "❌ Sorry, I couldn't write the email body right now."

def edit_email_body(original_draft, edit_instruction):
    """Edits an email draft based on user instructions."""
    if not GROK_API_KEY: return None
    prompt = f"""You are an email editor. Apply the user's requested change to the draft.
    Draft: --- {original_draft} ---
    Instruction: "{edit_instruction}"
    Return only the complete, new version of the email body.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=40)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok email editing error: {e}")
        return None

def translate_with_grok(text):
    """Translates text to a specified language."""
    if not GROK_API_KEY: return "❌ The AI API key is not configured."
    system_prompt = "You are a translation assistant. The user will provide text and specify the target language. Provide only the translated text."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=25)
        response.raise_for_status()
        translated_text = response.json()["choices"][0]["message"]["content"].strip()
        return f"🌍 Translated:\n\n_{translated_text}_"
    except Exception as e:
        print(f"Grok Translation error: {e}")
        return "⚠️ Sorry, the translation service is currently unavailable."
