import replicate
import uuid
import os
import requests  # needed for downloading the image

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")  # must be set in environment

replicate.Client(api_token=REPLICATE_API_TOKEN)

def generate_image(prompt):
    print("🎨 Prompt:", prompt)

    try:
        output = replicate.run(
            "stability-ai/sdxl:a9758cbf8a4f5fa5b017bf2f65ec9c0d5575551d7cb1199b1e14df3a0b3c9c65",
            input={"prompt": prompt}
        )

        print("🖼️ Output URLs:", output)

        if output and isinstance(output, list):
            image_url = output[0]
            image_path = f"/tmp/{uuid.uuid4().hex}.png"
            img_data = requests.get(image_url).content

            with open(image_path, "wb") as f:
                f.write(img_data)

            return image_path

        return None

    except Exception as e:
        print("❌ Replicate Error:", str(e))
        return None
