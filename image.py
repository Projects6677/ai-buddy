import os
import requests

STARRYAI_API_KEY = os.getenv("STARRYAI_API_KEY")

def generate_starryai_image(prompt):
    try:
        headers = {
            "Authorization": f"Token {STARRYAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "title": prompt,
            "prompt": prompt,
            "model": "sci-fi",  # you can also try "art", "photo-realistic" if supported
            "aspect_ratio": "square",  # options might include 'portrait', 'landscape'
            "samples": 1
        }

        response = requests.post("https://api.starryai.com/creations/", json=payload, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            image_url = data['data'][0]['url']  # Adjust depending on actual response format
            return image_url
        else:
            return f"❌ Failed to generate image: {response.status_code} - {response.text}"

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"
