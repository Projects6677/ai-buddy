import requests
import uuid
import os

# 🔑 Replace with your actual Stability AI API key
STABILITY_API_KEY = "sk-oWluAE2ObDCUrQmRdmPlcuPqfyc5uVl00Nr1eTWpf1afU4dc"

def generate_image(prompt):
    endpoint = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/png",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "output_format": "png",
    }

    print("🎨 Generating image for prompt:", prompt)
    response = requests.post(endpoint, headers=headers, json=payload)

    if response.status_code == 200:
        image_path = f"/tmp/{uuid.uuid4().hex}.png"
        with open(image_path, "wb") as f:
            f.write(response.content)
        print("✅ Image saved to", image_path)
        return image_path
    else:
        print("❌ Image generation failed:", response.status_code, response.text)
        return None
