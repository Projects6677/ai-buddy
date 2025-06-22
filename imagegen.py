import requests
import uuid
import os

# Replace with your actual Hugging Face token
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

def generate_image(prompt):
    endpoint = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Accept": "image/png",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
    }

    print("🎨 Sending request to Hugging Face for prompt:", prompt)
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        if response.status_code == 200:
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("✅ Image generated at:", image_path)
            return image_path
        else:
            print("❌ Hugging Face generation failed:", response.status_code, response.text)
            return None
    except Exception as e:
        print("❌ Exception occurred while generating image:", e)
        return None
