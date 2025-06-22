# image_gen.py
import openai
import os

# Automatically gets the API key from Render environment variables
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
    except openai.error.OpenAIError as e:
        print("❌ OpenAI API error:", e)
        return None
    except Exception as ex:
        print("❌ Unexpected error during image generation:", ex)
        return None
