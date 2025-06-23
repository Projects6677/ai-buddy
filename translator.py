# translator.py
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import torch

model_name = "facebook/m2m100_418M"
tokenizer = M2M100Tokenizer.from_pretrained(model_name)
model = M2M100ForConditionalGeneration.from_pretrained(model_name)

LANGUAGES = {
    "french": "fr",
    "german": "de",
    "telugu": "te",
    "tamil": "ta",
    "hindi": "hi",
    "spanish": "es",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "english": "en",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "turkish": "tr",
    "arabic": "ar",
    "bengali": "bn",
    "urdu": "ur",
    "malayalam": "ml",
    "gujarati": "gu"
}

def translate_text(text, target_lang_code):
    try:
        tokenizer.src_lang = "en"
        encoded = tokenizer(text, return_tensors="pt")
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=tokenizer.get_lang_id(target_lang_code)
        )
        return tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
    except Exception as e:
        return f"❌ Translation failed: {str(e)}"
