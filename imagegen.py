import replicate
import uuid
import requests
import os

# 🗝️ Must be set in your Render environment
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate.Client(api_token=REPLICATE_API_TOKEN)

def generate_image(prompt):
    print("🎨 Prompt:", prompt)
    try:
        output = replicate.run(
            "stability-ai/sdxl:7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
            input={
                "prompt": prompt,
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
        )

        if output and isinstance(output, list):
            url = output[0]
            print("🖼️ Image URL:", url)

            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            img_data = requests.get(url).content
            with open(image_path, "wb") as f:
                f.write(img_data)
            return image_path

    except Exception as e:
        print("❌ Replicate Error:", e)
    return None
