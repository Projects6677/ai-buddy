import requests
import uuid
import os
import base64

# ✅ Replace with your Stability API Key
STABILITY_API_KEY = "sk-Yhob1F0R41BvumjmZnZEiHNzYTmMcodrBKssStYNSVDV2Xaea"

def generate_image(prompt):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-512-v2-1/text-to-image"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 7,
        "height": 512,
        "width": 512,
        "samples": 1,
        "steps": 30
    }

    print("🎨 Generating image for prompt:", prompt)
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            base64_img = response.json()['artifacts'][0]['base64']
            image_data = base64.b64decode(base64_img)
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(image_path, "wb") as f:
                f.write(image_data)
            print("✅ Image saved to", image_path)
            return image_path
        except Exception as e:
            print("⚠️ Error parsing image:", e)
            return None
    else:
        print("❌ Image generation failed:", response.status_code, response.text)
        return None
