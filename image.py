# image.py

import requests
import time
import os

# ✅ Fetch StarryAI API key securely from environment variable
STARRYAI_API_KEY = os.getenv("STARRYAI_API_KEY")

def generate_starryai_image(prompt):
    if not STARRYAI_API_KEY:
        return "❌ StarryAI API key is missing. Please set it in the environment."

    headers = {
        "Authorization": f"Bearer {STARRYAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "model": "sci-fi"
    }

    try:
        # Step 1: Submit generation request
        response = requests.post("https://api.starryai.com/v1/generate", json=payload, headers=headers)
        if response.status_code != 200:
            return f"❌ Failed to start image generation: {response.text}"

        generation_id = response.json().get("id")
        if not generation_id:
            return "❌ No generation ID received."

        # Step 2: Poll until the image is ready
        for _ in range(10):  # Max wait time ~50 seconds
            status_response = requests.get(
                f"https://api.starryai.com/v1/generations/{generation_id}",
                headers=headers
            )
            if status_response.status_code != 200:
                time.sleep(5)
                continue

            status_data = status_response.json()
            if status_data.get("status") == "completed":
                return status_data.get("image_url")

            time.sleep(5)

        return "⚠️ Image generation is taking too long. Try again later."

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"
