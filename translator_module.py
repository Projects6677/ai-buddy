# translator_module.py
from transformers import pipeline

# Lightweight models
translator_en_to_fr = pipeline("translation_en_to_fr", model="t5-small")
translator_fr_to_en = pipeline("translation", model="Helsinki-NLP/opus-mt-fr-en")

def translate_text(text):
    try:
        # Auto-detect if input is French or English based on first characters (simple logic)
        if any(char in text.lower() for char in "éàçèùôîï"):  # assume French input
            result = translator_fr_to_en(text)
        else:
            result = translator_en_to_fr(text)
        return result[0]['translation_text']
    except Exception as e:
        print("Translation error:", e)
        return "❌ Translation failed. Try again."
