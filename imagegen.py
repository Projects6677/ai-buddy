import requests
import time
import uuid

REPLICATE_API_TOKEN = "r8_Q9HsRNKWQaRMnm2zTflnkJkujCyMzKB0hnQHe"

def generate_image(prompt):
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "version": "a9758cb6c0c5fcb385d2e11a6a9297e27d2c62e383271a225881269569c65f41",  # stable-diffusion-v1.5
        "input": {"prompt": prompt}
    }

    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    if response.status_code != 201:
        print("❌ Failed to start image generation:", response.text)
        return None

    prediction = response.json()
    prediction_id = prediction["id"]

    while True:
        poll_response = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}", headers=headers)
        result = poll_response.json()
        status = result["status"]

        if status == "succeeded":
            image_url = result["output"][0]
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            img_data = requests.get(image_url).content
            with open(image_path, "wb") as f:
                f.write(img_data)
            return image_path
        elif status in ["failed", "canceled"]:
            print("❌ Image generation failed:", result)
            return None

        time.sleep(2)
