# image_gen.py
from craiyon import Craiyon  # pip install craiyon.py

# Use default model: "art", or "drawing", or "photo"
generator = Craiyon()  # Default is art mode

def generate_image_url(prompt):
    try:
        print("🧠 Generating image via Craiyon for prompt:", prompt)
        result = generator.generate(prompt, model_type="photo")  # try "art", "drawing" too
        if result and result.images:
            url = result.images[0]
            print("✅ Image URL:", url)
            return url
        else:
            print("❌ No images generated")
            return None
    except Exception as e:
        print("❌ Craiyon generation error:", e)
        return None
