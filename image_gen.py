# image_gen.py
import openai
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

def generate_image_url(prompt):
    try:
        print("🧠 Generating image for prompt:", prompt)
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        image_url = response["data"][0]["url"]
        print("✅ Image URL:", image_url)
        return image_url
    except Exception as e:
        print("❌ Error during image generation:", e)
        return None
