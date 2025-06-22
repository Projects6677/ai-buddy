import requests
import uuid
import os
import time

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
MODEL_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"

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
    print("📤 Sending request to Hugging Face endpoint:", MODEL_URL)

    try:
        response = requests.post(MODEL_URL, headers=headers, json=payload)
        print("🧾 Response status code:", response.status_code)

        if response.status_code == 503:
            print("⏳ Model is loading, waiting...")
            time.sleep(10)
            response = requests.post(MODEL_URL, headers=headers, json=payload)

        if response.status_code == 200:
            file_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(file_path, "wb") as f:
                f.write(response.content)
            print("✅ Image saved at:", file_path)
            return file_path

        print("❌ Generation failed.")
        print("📩 Response text:", response.text)
        return None

    except Exception as e:
        print("🔥 Exception occurred:", str(e))
        return None
