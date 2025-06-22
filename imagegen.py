import requests
import uuid
import time
import os

# Hugging Face API key should be stored in environment variable
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

def generate_image(prompt):
    if not HUGGINGFACE_TOKEN:
        print("❌ ERROR: Hugging Face API key not set in environment variable 'HUGGINGFACE_TOKEN'")
        return None

    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Accept": "image/png",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt
    }

    print(f"🎨 Prompt: {prompt}")
    print(f"📤 Sending request to Hugging Face endpoint: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"🧾 Response status code: {response.status_code}")

        # Handle cold start
        if response.status_code == 503:
            print("⏳ Model is loading on Hugging Face... retrying in 10 seconds.")
            time.sleep(10)
            response = requests.post(url, headers=headers, json=payload)
            print(f"🧾 Retry response status code: {response.status_code}")

        # If success
        if response.status_code == 200:
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Image saved to {image_path}")
            return image_path

        # Other errors
        print("❌ Generation failed.")
        print("📩 Response text:", response.text)
        return None

    except Exception as e:
        print("🔥 Exception occurred:", str(e))
        return None
