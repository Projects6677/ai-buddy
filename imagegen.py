import openai
import requests
import os
import uuid

# Set your OpenAI API key securely in environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

def generate_image(prompt):
    print(f"🎨 Prompt: {prompt}")

    try:
        # Create the image using OpenAI DALL·E
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512",
            response_format="url"
        )

        image_url = response['data'][0]['url']
        print(f"🌐 Image URL: {image_url}")

        # Download and save the image
        image_data = requests.get(image_url).content
        file_path = f"/tmp/{uuid.uuid4().hex}.png"
        with open(file_path, "wb") as f:
            f.write(image_data)

        print("✅ Image downloaded and saved to:", file_path)
        return file_path

    except Exception as e:
        print("❌ OpenAI Image Generation Error:", e)
        return None
