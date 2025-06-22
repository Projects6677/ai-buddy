import requests
import uuid
import os
import time

# ✅ Set this in Render Environment as: HUGGINGFACE_TOKEN = your_token
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# ✅ Recommended Hugging Face model that is public and API-ready
MODEL_URL = "https://api-inference.huggingface.co/models/stabilityai/sdxl-turbo"

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
        print("🧾 Status:", response.status_code)

        if response.status_code == 503:
            print("⏳ Model loading... retrying in 10s")
            time.sleep(10)
            response = requests.post(MODEL_URL, headers=headers, json=payload)

        if response.status_code == 200:
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Image saved:", image_path)
            return image_path

        print("❌ Generation failed. Response:", response.text)
        return None

    except Exception as e:
        print("🔥 Exception:", str(e))
        return None
