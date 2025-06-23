# image_gen_hf.py
import requests
import os

API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
headers = {
    "Authorization": f"Bearer {os.getenv('HF_API_KEY')}",
    "Content-Type": "application/json"
}

def generate_image_url(prompt):
    try:
        print("🧠 Generating image via Hugging Face for prompt:", prompt)

        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code != 200:
            print("❌ HF API Error:", response.text)
            return None

        # Save image to temp and return path
        image_path = "/tmp/generated_image.png"
        with open(image_path, "wb") as f:
            f.write(response.content)

        print("✅ Image generated and saved at:", image_path)
        return image_path

    except Exception as e:
        print("❌ HF Generation error:", e)
        return None
