import requests
import uuid
import os
import time

# ✅ Set your Hugging Face token in Render Environment: HUGGINGFACE_TOKEN
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# ✅ Public model that works with Inference API
MODEL_URL = "https://api-inference.huggingface.co/models/digiplay/anything-v4.5"

def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "image/png"
    }

    payload = {
        "inputs": prompt
    }

    print("🎨 Prompt:", prompt)
    print("📤 Sending request to:", MODEL_URL)

    try:
        response = requests.post(MODEL_URL, headers=headers, json=payload)
        print("🧾 Status code:", response.status_code)

        if response.status_code == 503:
            print("⏳ Model loading... retrying in 10 seconds")
            time.sleep(10)
            response = requests.post(MODEL_URL, headers=headers, json=payload)

        if response.status_code == 200:
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Image saved:", image_path)
            return image_path

        print("❌ Failed to generate image.")
        print("📩 Response text:", response.text)
        return None

    except Exception as e:
        print("🔥 Exception occurred:", str(e))
        return None
