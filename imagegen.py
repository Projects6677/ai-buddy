import requests
import uuid
import os
import time

# 👇 Use Render Environment Variable for security
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

MODEL_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"

def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "image/png"
    }

    styled_prompt = f"{prompt}, mdjrny-v4 style"
    payload = { "inputs": styled_prompt }

    print("🎨 Prompt:", styled_prompt)
    print("📤 Sending request to:", MODEL_URL)

    try:
        response = requests.post(MODEL_URL, headers=headers, json=payload)
        print("🧾 Status code:", response.status_code)

        if response.status_code == 503:
            print("⏳ Model is loading. Retrying in 10s...")
            time.sleep(10)
            response = requests.post(MODEL_URL, headers=headers, json=payload)

        if response.status_code == 200:
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Image saved:", image_path)
            return image_path

        print("❌ Failed to generate image.")
        print("📩 Response:", response.text)
        return None

    except Exception as e:
        print("🔥 Error:", str(e))
        return None
