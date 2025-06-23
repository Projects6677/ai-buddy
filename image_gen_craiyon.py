# image_gen_craiyon.py
from craiyon import Craiyon  # pip install craiyon.py

# Set default mode
generator = Craiyon("art")  # Can be changed to "photo" or "drawing"

def set_craiyon_mode(mode: str):
    global generator
    try:
        generator = Craiyon(mode)
        print(f"🖌️ Craiyon mode set to: {mode}")
    except Exception as e:
        print("❌ Failed to set Craiyon mode:", e)

def generate_image_url(prompt):
    try:
        print("🧠 Generating image for prompt:", prompt)
        result = generator.generate(prompt)
        if result and result.images:
            url = result.images[0]
            print("✅ Image URL:", url)
            return url
        else:
            print("❌ No image returned from Craiyon")
            return None
    except Exception as e:
        print("❌ Craiyon error:", e)
        return None
