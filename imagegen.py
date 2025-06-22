import openai
import os
import requests
import uuid

# Get your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_image(prompt):
    print(f"🎨 Generating image with prompt: {prompt}")
    
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
            response_format="url"
        )

        image_url = response.data[0].url
        print(f"🌐 Image URL: {image_url}")

        # Download image
        image_data = requests.get(image_url).content
        file_path = f"/tmp/{uuid.uuid4().hex}.png"
        with open(file_path, "wb") as f:
            f.write(image_data)

        print(f"✅ Image saved to {file_path}")
        return file_path

    except openai.OpenAIError as e:
        print("❌ OpenAI Image Generation Error:", e)
    except Exception as e:
        print("❌ Unexpected Error:", e)

    return None
