import requests
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Replace with actual URL

def ai_reply(prompt):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",  # or whatever model name applies
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(GROK_API_URL, headers=headers, json=data)
        result = response.json()
        
        # Adjust based on actual response format
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            return reply.strip()
        else:
            return "❌ Grok API returned no reply."

    except Exception as e:
        return f"⚠️ Grok API error: {e}"
