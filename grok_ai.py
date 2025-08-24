# grok_ai.py
import os
import json
from datetime import datetime
import google.generativeai as genai

# --- Configuration ---
# Use a placeholder for the API key in the code. Set the actual key in your .env file.
# The `genai` library will automatically pick it up from the environment variable.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not set. Some features will be disabled.")


# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing,
    including a culturally-aware greeting.
    """
    if not GEMINI_API_KEY:
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Have a great day!",
            "detailed_history": "No historical fact found for today.",
            "detailed_weather": "Weather data is currently unavailable."
        }
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result_text = response.text
        return json.loads(result_text)
    except Exception as e:
        print(f"Gemini unified briefing error: {e}")
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Could not generate explanation.",
            "detailed_history": "Could not generate historical fact.",
            "detailed_weather": "Could not generate weather forecast."
        }


# --- PRIMARY INTENT ROUTER ---
def route_user_intent(text):
    if not GEMINI_API_KEY:
        return {"intent": "general_query", "entities": {}}

    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are an expert AI routing system for a WhatsApp assistant. Your job is to analyze the user's text and classify it into one of the predefined intents.
    You MUST respond with a JSON object containing two keys: "intent" and "entities".

    The current date is: {datetime.now().strftime('%Y-%m-%d %A, %H:%M:%S')}

    Here are the possible intents and the required entities for each:

    1. "set_reminder":
       - Triggered by requests to be reminded of something.
       - "entities": An ARRAY of objects, each with {{"task": "The core task of the reminder, e.g., 'call John'", "timestamp": "The fully resolved date and time for the reminder in 'YYYY-MM-DD HH:MM:SS' format. You MUST resolve relative times like '8pm today' or 'tomorrow at 4pm' based on the current date.", "recurrence": "The recurrence rule if mentioned (e.g., 'every day'), otherwise null"}}

    2. "get_reminders":
       - Triggered by requests to see, check, show, or list all active reminders.
       - "entities": {{}}

    3. "log_expense":
       - "entities": An array of objects, each with {{"cost": <number>, "item": "description", "place": "store_name_or_null", "timestamp": "The fully resolved date and time for the expense in 'YYYY-MM-DD HH:MM:SS' format. If a time is mentioned, use it. If no time or date is mentioned, use the current date and time."}}

    4. "convert_currency":
       - "entities": An array of objects, each with {{"amount": <number>, "from_currency": "3-letter_code", "to_currency": "3-letter_code"}}

    5. "get_weather":
       - "entities": {{"location": "city_name"}}

    6. "export_expenses":
       - Triggered by requests to export expenses to an Excel file.
       - "entities": {{}}
       
    7. "get_expense_sheet":
       - Triggered by requests to get a link to the Google Sheet for expenses.
       - "entities": {{}}

    8. "youtube_search":
       - Triggered by requests to find, search for, or get a video from YouTube.
       - "entities": {{"query": "The search term for the video."}}

    9. "drive_search_file":
       - Triggered by requests to find or search for a file in Google Drive.
       - "entities": {{"query": "The name or keyword of the file to search for."}}

    10. "drive_analyze_file":
        - Triggered by requests to summarize, analyze, or ask questions about a specific file in Google Drive.
        - "entities": {{"filename": "The exact or partial filename to analyze."}}

    11. "drive_upload_file":
        - Triggered by requests to save or upload the *next* file to Google Drive. This is used when the user *has not* sent the file yet but is indicating they want to.
        - "entities": {{}}

    12. "general_query":
        - This is the default intent for any other general question or command.
        - "entities": {{}}

    ---
    User's text to analyze: "{text}"
    ---

    Return only the JSON object.
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result_text = response.text
        return json.loads(result_text)
    except Exception as e:
        print(f"Gemini intent routing error: {e}")
        return {"intent": "general_query", "entities": {}}


# --- OTHER AI FUNCTIONS ---
def analyze_document_context(text):
    if not GEMINI_API_KEY or not text or not text.strip(): return None
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""You are an expert document analysis AI. Read the following text and determine its type and extract key information. Your response MUST be a JSON object with two keys: "doc_type" and "data". Possible "doc_type" values are: "resume", "project_plan", "meeting_invite", "q_and_a", "generic_document". The "data" key should be an empty object `{{}}` unless it's a "meeting_invite", in which case it should be `{{"task": "description of event", "timestamp": "YYYY-MM-DD HH:MM:SS"}}`. The current date is {datetime.now().strftime('%Y-%m-%d %A')}. Here is the text to analyze: --- {text} --- Return only the JSON object."""
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini document context analysis error: {e}")
        return None

def multi_modal_image_analysis(image_path, question):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured."
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        image_part = genai.upload_file(image_path)
        prompt = f"""Analyze the image and answer the following question: "{question}" """
        response = model.generate_content([image_part, prompt])
        return response.text
    except Exception as e:
        print(f"Gemini multi-modal analysis error: {e}")
        return "⚠️ Sorry, I had trouble analyzing that image."

def get_contextual_ai_response(document_text, question):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured."
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""You are an AI assistant with a document's content loaded into your memory. A user is now asking a question about this document. Your task is to answer their question based *only* on the information provided in the document text. Here is the full text of the document: --- DOCUMENT START --- {document_text} --- DOCUMENT END --- Here is the user's question: "{question}". Provide a direct and helpful answer. If the answer cannot be found in the document, say "I couldn't find the answer to that in the document." """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini contextual response error: {e}")
        return "⚠️ Sorry, I had trouble answering that question."

def is_document_followup_question(text):
    if not GEMINI_API_KEY: return True
    model = genai.GenerativeModel('gemini-1.5-flash')
    command_keywords = ["remind me", "hi", "hello", "hey", "menu", "what's the weather", "convert", "translate", "fix grammar", "my expenses", "send an email", ".dev", ".test", ".nuke", ".stats"]
    if any(keyword in text.lower() for keyword in command_keywords):
        return False
    prompt = f"""A user has previously uploaded a document and is in a follow-up conversation. Their new message is: "{text}". Is this message a question or command related to the document (e.g., "summarize it", "what are the key points?")? Or is it a completely new, unrelated command? Respond with only the word "yes" if it is a follow-up, or "no" if it is a new command."""
    try:
        response = model.generate_content(prompt)
        return "yes" in response.text.strip().lower()
    except Exception as e:
        print(f"Gemini context check error: {e}")
        return True

def ai_reply(prompt):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured. This feature is disabled."
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Gemini AI error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now."

def correct_grammar_with_grok(text):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured. This feature is disabled."
    model = genai.GenerativeModel('gemini-1.5-flash')
    system_prompt = "You are an expert grammar and spelling correction assistant. Correct the user's text. Only return the corrected text, without any explanation or preamble."
    try:
        res = model.generate_content([system_prompt, text])
        corrected_text = res.text.strip().strip('"')
        return f"✅ Corrected:\n\n_{corrected_text}_"
    except Exception as e:
        print(f"Gemini Grammar error: {e}")
        return "⚠️ Sorry, the grammar correction service is unavailable."

def analyze_email_subject(subject):
    if not GEMINI_API_KEY: return None
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""You are an email assistant. The user wants to write an email with the subject: "{subject}". What are the 2-3 most important follow-up questions you should ask to get the necessary details to write this email? Return your answer as a JSON object with a single key "questions" which is an array of strings. For a 'leave' subject, ask for dates and reason. For a 'meeting request' subject, ask for topic, date/time, and attendees. For a generic subject, just ask for the main point of the email. Only return the JSON object."""
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text).get("questions")
    except Exception as e:
        print(f"Gemini subject analysis error: {e}")
        return None

def write_email_body_with_grok(prompt):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured. This feature is disabled."
    model = genai.GenerativeModel('gemini-1.5-flash')
    system_prompt = "You are an expert email writing assistant. Based on the user's prompt, write a clear, professional, and well-formatted email body. Your entire response must consist *only* of the email body text. Do not include a subject line, greetings like 'Hello,', sign-offs like 'Sincerely,', or any preamble like 'Here is the email body:'."
    try:
        res = model.generate_content([system_prompt, prompt])
        return res.text.strip()
    except Exception as e:
        print(f"Gemini email writing error: {e}")
        return "❌ Sorry, I couldn't write the email body right now."

def edit_email_body(original_draft, edit_instruction):
    if not GEMINI_API_KEY: return None
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""You are an email editor. Here is an email draft: --- DRAFT --- {original_draft} --- END DRAFT --- The user wants to make a change. Their instruction is: "{edit_instruction}". Apply the change and return only the complete, new version of the email body."""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini email editing error: {e}")
        return None

def translate_with_grok(text):
    if not GEMINI_API_KEY: return "❌ The Gemini API key is not configured. This feature is disabled."
    model = genai.GenerativeModel('gemini-1.5-flash')
    system_prompt = "You are a translation assistant. The user will provide text to be translated, and they will specify the target language. Your task is to provide the translation. Only return the translated text."
    try:
        response = model.generate_content([system_prompt, text])
        translated_text = response.text.strip()
        return f"🌍 Translated:\n\n_{translated_text}_"
    except Exception as e:
        print(f"Gemini Translation error: {e}")
        return "⚠️ Sorry, the translation service is currently unavailable."
