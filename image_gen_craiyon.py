import base64
import os
import requests

# Craiyon uses simple POST API to generate images
def generate_image_url(prompt):
    try:
        print("🧠 Generating image for prompt:", prompt)

        response = requests.post(
            "https://backend.craiyon.com/generate",
            json={"prompt": prompt},
            timeout=60
        )

        if response.status_code != 200:
            print("❌ Craiyon API failed with status:", response.status_code)
            return None

        data = response.json()
        if "images" not in data or not data["images"]:
            print("❌ No images returned from Craiyon")
            return None

        # Decode the first image from base64 and save it
        image_data = base64.b64decode(data["images"][0])
        save_path = "/tmp/generated_image.jpg"
        with open(save_path, "wb") as f:
            f.write(image_data)

        print("✅ Image saved to:", save_path)
        return save_path

    except Exception as e:
        print("❌ Error generating image with Craiyon:", e)
        return None
