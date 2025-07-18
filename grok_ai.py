# grok_ai.py
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL = "llama3-70b-8192"
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# --- Main AI Chat Function ---
def ai_reply(prompt):
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured. This feature is disabled."
        
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok AI error: {e}")
        return "⚠️ Sorry, I couldn't connect to the AI service right now."

# --- Grammar Correction Function ---
def correct_grammar_with_grok(text):
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured. This feature is disabled."

    system_prompt = """
    You are an expert grammar and spelling correction assistant.
    Correct the user's text. If the text is heavily misspelled or jumbled,
    interpret the user's likely intent and provide the most logical, natural-sounding correction.
    Only return the corrected text, without any explanation, preamble, or quotation marks.
    For example, if the user says 'herrr are you', the likely intent is 'How are you?'.
    """
    
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.2
    }

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

# --- AI Parsing Functions ---
def parse_expense_with_grok(text):
    if not GROK_API_KEY: return None
    prompt = f"""
    You are an expert expense parsing assistant. Your task is to extract all expenses from the user's text.
    The text is: "{text}"
    Extract the cost (as a number), the item purchased, the place of purchase (if mentioned), and the timestamp (if mentioned).
    Return the result as a JSON object with a single key "expenses" which is an array of objects. 
    Each object must have keys "cost", "item", "place", and "timestamp".
    If a place or timestamp is not mentioned, set its value to null.
    Only return the JSON object, with no other text or explanation.
    """
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
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
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
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
    payload = {
        "model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result_text)
        return result_data.get("conversions")
    except Exception as e:
        print(f"Grok currency parsing error: {e}")
        return None
