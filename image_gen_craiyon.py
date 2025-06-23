def send_image_to_user(to, image_path):
    upload_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    files = {"file": ("generated_image.jpg", open(image_path, "rb"), "image/jpeg")}
    data = {"messaging_product": "whatsapp"}

    media_response = requests.post(upload_url, headers=headers, files=files, data=data)
    media_id = media_response.json().get("id")

    if media_id:
        message_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {
                "id": media_id,
                "caption": "Here is your generated image!"
            }
        }
        requests.post(message_url, headers=headers, json=payload)
