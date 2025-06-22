# ✅ imagegen.py (using DeepAI)
import requests
import uuid
import os

DEEP_AI_API_KEY = "19ff8563-9efc-477a-b167-454481815fa5"

def generate_image(prompt):
    print("\U0001F3A8 Prompt:", prompt)
    try:
        response = requests.post(
            "https://api.deepai.org/api/text2img",
            data={'text': prompt},
            headers={'api-key': DEEP_AI_API_KEY}
        )

        if response.status_code == 200:
            image_url = response.json().get("output_url")
            if not image_url:
                print("❌ No image URL returned")
                return None

            print("✅ Image URL:", image_url)
            # Download image
            img_data = requests.get(image_url).content
            file_path = f"/tmp/{uuid.uuid4().hex}.png"
            with open(file_path, "wb") as f:
                f.write(img_data)
            return file_path

        else:
            print("❌ DeepAI Error:", response.status_code, response.text)
            return None

    except Exception as e:
        print("❌ Exception:", e)
        return None
