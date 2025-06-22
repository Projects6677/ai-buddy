# image_gen.py
import openai
import os

# Get OpenAI key from Render's environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY")

def generate_image_url(prompt):
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        return response["data"][0]["url"]
    except Exception as e:
        print("❌ Image generation failed:", e)
        return None
