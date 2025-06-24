import requests
import os

# Set your Hugging Face API token
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

API_URLS = {
    "en_to_fr": "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-fr",
    "fr_to_en": "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-fr-en"
}

def translate_text(text):
    try:
        if ":" not in text:
            return "⚠️ Please use `en:` or `fr:` format like:\n`en: I am happy`"

        lang_prefix, content = text.split(":", 1)
        content = content.strip()
        lang_prefix = lang_prefix.strip().lower()

        if lang_prefix == "en":
            direction = "en_to_fr"
        elif lang_prefix == "fr":
            direction = "fr_to_en"
        else:
            return "⚠️ Unsupported language prefix. Use `en:` or `fr:`."

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }
        payload = {"inputs": content}
        url = API_URLS[direction]

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        output = response.json()

        return f"🌍 Translated: {output[0]['translation_text']}"

    except Exception as e:
        print("Translation error:", e)
        return "❌ Translation failed."
