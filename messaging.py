import requests
import os

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN") or "EAAJ0jnn2gyMBO7qaQPmalfFVqusr5zoZCuSwPy148FvvWzQA1CGhBgiPVJS4SHhNdAzAo9UHqHaQhHZCMPIB9BRzdIETq2grq2HwVBzrS3YbmRfYu3RUG3oQJ4ZCviyFhCK7q2IVhntst6ZAG6BGjGhsLZAVQLHXvSqxeWcNw9QwE0ZAgBnPF7tRtmqgj6BcfPxZA99LIrVz0gdwV7DJ4aXTPwLBzOSHr64v2CUPFmok8ZB3EQZDZD"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") or "698497970011796"

def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    requests.post(url, headers=headers, json=data)
