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

def get_smart_greeting(user_name, festival_name=None):
    """
    Generates a smart greeting. If a festival name is provided, it creates a festive
    greeting for it. Otherwise, it returns a standard greeting.
    """
    if not GROK_API_KEY:
        if festival_name:
            return f"Happy {festival_name}, {user_name}!"
        return f"☀️ Good Morning, {user_name}!"
    
    if festival_name:
        # If we know it's a festival, the AI's only job is to be creative.
        prompt = f"""
        You are an AI assistant that writes creative, cheerful greetings.
        Today is {festival_name} in India.
        Write a short, festive greeting for a user named {user_name}.
        
        Example for Raksha Bandhan: "Happy Raksha Bandhan, {user_name}!"
        Example for Diwali: "Wishing you a bright and joyful Diwali, {user_name}!"

        Return only the single line of greeting text.
        """
    else:
        # If it's not a festival, just give a standard greeting.
        prompt = f"""
        You are an AI assistant that writes a standard morning greeting.
        Write a simple, cheerful greeting for a user named {user_name}.
        
        Example: "☀️ Good Morning, {user_name}!"

        Return only the single line of greeting text.
        """

    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok smart greeting error: {e}")
        return f"☀️ Good Morning, {user_name}!"

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

# --- MODIFICATION: CULTURALLY-AWARE GREETING ---
def get_smart_greeting(user_name):
    if not GROK_API_KEY: return f"☀️ Good Morning, {user_name}!"
    
    prompt = f"""
    You are an AI assistant with a deep understanding of Indian culture, festivals, and significant national days. Your persona is that of a helpful Indian friend.
    Your task is to generate a cheerful morning greeting for a user named {user_name}.
    Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.

    Follow these rules strictly:
    1.  **Prioritize Indian Festivals:** First, check if today is a major Indian festival (like Raksha Bandhan, Diwali, Holi, Eid, Dussehra, Janmashtami, Ganesh Chaturthi), a national holiday (like Independence Day, Republic Day, Gandhi Jayanti), or a significant regional festival (like Onam, Pongal, Bihu).
    2.  **Generate a Festive Greeting:** If it is a major Indian event, create a short, festive greeting. For example: "Happy Raksha Bandhan, {user_name}!" or "Wishing you a joyful Diwali, {user_name}!".
    3.  **Secondary Check for Global Events:** If it is NOT a major Indian event, you can then check for widely recognized international days that are popular in India (like Friendship Day, New Year's Day, Valentine's Day).
    4.  **Default Greeting:** If it is not a special day according to the rules above, just return a standard, cheerful greeting: "☀️ Good Morning, {user_name}!"
    5.  **Exclusion:** Do NOT mention obscure or region-specific holidays from other countries (e.g., American Independence Day, specific European saints' days).

    Return only the single line of greeting text.
    """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6 }
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
