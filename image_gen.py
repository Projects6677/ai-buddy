# image_gen.py
import openai
import os

# Initialize the OpenAI client with the environment-stored API key
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_image_url(prompt):
    try:
        print("🧠 Generating image for prompt:", prompt)
        
        # Image generation using the required model
        response = client.images.generate(
            model="dall-e-2",            # ✅ Required model
            prompt=prompt,
            n=1,
            size="512x512",
            response_format="url"
        )

        # Extract image URL
        image_url = response.data[0].url
        print("✅ Image URL:", image_url)
        return image_url

    except Exception as e:
        print("❌ Error during image generation:", e)
        return None
