import requests
import os

GROK_API_KEY = os.getenv("GROK_API_KEY") or "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"

GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL = "llama3-70b-8192"

def ai_answer(prompt):
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload)
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Grok AI error: {str(e)}"

def correct_grammar_with_grok(text):
    prompt = f"Correct the grammar of this sentence: {text}. Only return the corrected sentence."
    
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful grammar assistant. Always reply with only the corrected sentence."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload)
        return "📝 Corrected: " + res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Grok Grammar error: {str(e)}"
