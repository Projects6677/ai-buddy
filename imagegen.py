import requests
import uuid

# 🔑 Your DeepAI API Key
DEEPAI_API_KEY = "a6f5c646-e0ab-4cff-a515-39ed2e4a867a"

def generate_image(prompt):
    print("🎨 Starting image generation...")
    url = "https://api.deepai.org/api/text2img"
    headers = {
        "api-key": DEEPAI_API_KEY,
    }
    data = {
        "text": prompt,
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        print("🔄 DeepAI API response status:", response.status_code)

        if response.status_code != 200:
            print("❌ API call failed:", response.text)
            return None

        json_response = response.json()
        print("📦 API JSON response:", json_response)

        output_url = json_response.get("output_url")
        if not output_url:
            print("❌ output_url missing in response")
            return None

        print("✅ Image URL:", output_url)

        # Download the image
        image_data = requests.get(output_url).content
        image_path = f"/tmp/{uuid.uuid4().hex}.png"

        with open(image_path, "wb") as f:
            f.write(image_data)

        print("📁 Image saved successfully to:", image_path)
        return image_path

    except Exception as e:
        print("🚨 Exception during image generation:", e)
        return None

