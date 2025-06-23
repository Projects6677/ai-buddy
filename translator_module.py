# translator_module.py
from transformers import MarianMTModel, MarianTokenizer

# Preload lightweight model (English ↔ French as an example)
model_name = "Helsinki-NLP/opus-mt-mul-en"
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)

def translate_to_english(text):
    try:
        # Tokenize and translate
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        translated = model.generate(**inputs)
        english_text = tokenizer.decode(translated[0], skip_special_tokens=True)
        return english_text
    except Exception as e:
        print("❌ Translation error:", e)
        return "❌ Failed to translate text."
