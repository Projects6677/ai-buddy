import requests
import os

HF_API_KEY = os.environ.get("HF_API_KEY")  # Set this in Render environment
API_URL = "https://api-inference.huggingface.co/models/stabilityai/sdxl-turbo"

headers = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Accept": "image/png"
}

def generate_image_url(prompt):
    try:
        print("🧠 Generating image via Hugging Face for prompt:", prompt)
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})

        if response.status_code != 200:
            print(f"❌ HF API Error: {response.status_code} - {response.text}")
            return None

        image_path = "/tmp/generated_image.jpg"
        with open(image_path, "wb") as f:
            f.write(response.content)

        return image_path

    except Exception as e:
        print("❌ Unexpected error:", e)
        return None
