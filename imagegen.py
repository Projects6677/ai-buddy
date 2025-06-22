import openai
import requests
import uuid
import os

# 🔐 Set your OpenAI API key securely via environment variable on Render
openai.api_key = os.environ.get("OPENAI_API_KEY")

def generate_image(prompt):
    print(f"🎨 Generating image with prompt: {prompt}")

    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        print("📸 Image URL received:", image_url)

        # Download image
        image_data = requests.get(image_url).content
        filename = f"/tmp/{uuid.uuid4().hex}.png"

        with open(filename, "wb") as f:
            f.write(image_data)

        print("✅ Image saved to:", filename)
        return filename

    except Exception as e:
        print("❌ Error generating image:", str(e))
        return None
