import requests
import os

SAPLING_API_KEY = os.getenv("SAPLING_API_KEY") or "8N9ZGV0S82H2FVAS7GNFUB4JMZ8DV52J"

def correct_grammar(text):
    url = "https://api.sapling.ai/api/v1/edits"
    headers = {
        "Authorization": f"Bearer {SAPLING_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "session_id": "whatsapp-bot-ranga"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        # Print raw response for debugging
        print(">>> STATUS CODE:", response.status_code)
        print(">>> HEADERS:", response.headers)
        print(">>> TEXT:", response.text)

        # Try parsing JSON
        result = response.json()

        if "edits" not in result or not result["edits"]:
            return "✅ No grammar issues found."

        corrected_text = text
        for edit in reversed(result["edits"]):
            start = edit["start"]
            end = edit["end"]
            replacement = edit["replacement"]
            corrected_text = corrected_text[:start] + replacement + corrected_text[end:]

        return f"📝 Corrected: {corrected_text}"

    except Exception as e:
        return f"⚠️ Sapling API error: {str(e)}"
