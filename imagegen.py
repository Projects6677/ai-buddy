import requests
import time
import uuid
import os

REPLICATE_API_TOKEN = "r8_Q9HsRNKWQaRMnm2zTflnkJkujCyMzKB0hnQHe"

def generate_image(prompt):
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "version": "db21e45f3703a403ca2724d3fd39c85e8f82d0a1ccf1185df1c3ff54d5c9e8ff",  # sdxl model
        "input": {"prompt": prompt}
    }

    # Step 1: Create prediction
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    if response.status_code != 201:
        print("❌ Failed to start image generation:", response.text)
        return None

    prediction = response.json()
    prediction_id = prediction["id"]
    status = prediction["status"]

    # Step 2: Poll for completion
    while status not in ["succeeded", "failed", "canceled"]:
        time.sleep(1)
        poll_response = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}", headers=headers)
        status = poll_response.json()["status"]

    if status == "succeeded":
        output_url = poll_response.json()["output"][0]
        print("✅ Image generated:", output_url)

        # Download the image
        image_path = f"/tmp/{uuid.uuid4().hex}.png"
        img_data = requests.get(output_url).content
        with open(image_path, "wb") as f:
            f.write(img_data)
        return image_path
    else:
        print("❌ Image generation failed:", status)
        return None
