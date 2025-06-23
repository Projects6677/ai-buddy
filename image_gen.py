# image_gen.py
import openai
import os
import traceback

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_image_url(prompt):
    try:
        print("🧠 Generating DALL·E 3 image for prompt:", prompt)

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",  # or "gpt-4" depending on availability
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Generate an image for this prompt: {prompt}"
                        }
                    ]
                }
            ],
            tools=[{"type": "image_generation"}],
            tool_choice="auto",
        )

        image_url = response.choices[0].message.tool_calls[0].function.arguments['url']
        print("✅ DALL·E 3 Image URL:", image_url)
        return image_url

    except Exception as e:
        print("❌ DALL·E 3 generation error:", e)
        traceback.print_exc()
        return None
