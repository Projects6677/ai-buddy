# translator_module.py
import requests
import os

# Set your Hugging Face API token (set it in your .env on Render)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URLS = {
    "en_to_fr": "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-fr",
    "fr_to_en": "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-fr-en"
}

def translate_text(text, direction="fr_to_en"):
    try:
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }
        payload = {"inputs": text}
        url = API_URLS[direction]
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        translated = response.json()[0]['translation_text']
        return translated
    except Exception as e:
        print("Translation error:", e)
        return "⚠️ Failed to translate."
