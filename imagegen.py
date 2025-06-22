import replicate
import os
import uuid

# Get your API token from Render env
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

def generate_image(prompt):
    print("🎨 Prompt:", prompt)
    try:
        # Set your token
        replicate.Client(api_token=REPLICATE_API_TOKEN)

        # Call SDXL model
        output = replicate.run(
            "stability-ai/sdxl:latest",
            input={"prompt": prompt}
        )

        # output is a list of image URLs
        if output:
            print("✅ Image URL:", output[0])
            image_url = output[0]
            image_path = f"/tmp/{uuid.uuid4().hex}.png"

            # Download the image
            img_data = requests.get(image_url).content
            with open(image_path, "wb") as handler:
                handler.write(img_data)

            return image_path
        else:
            print("❌ No image returned.")
            return None

    except Exception as e:
        print("❌ Replicate Error:", e)
        return None
