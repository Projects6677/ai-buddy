# translator_module.py
from transformers import pipeline

# Load lightweight translation pipelines
translator_en_to_any = pipeline("translation_en_to_fr", model="t5-small")   # example: English to French
translator_any_to_en = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-en")

def translate_text(text, direction="any_to_en"):
    try:
        if direction == "en_to_any":
            result = translator_en_to_any(text)
        else:
            result = translator_any_to_en(text)
        return result[0]['translation_text']
    except Exception as e:
        print("Translation error:", e)
        return "❌ Failed to translate. Please try again."
