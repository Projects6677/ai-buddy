import requests
import os

# Example: Weather API via Open-Meteo
def get_weather(location):
    try:
        # Use Open-Meteo geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geo_response = requests.get(geo_url)
        geo_data = geo_response.json()

        if "results" not in geo_data or len(geo_data["results"]) == 0:
            return "⚠️ Couldn't find that location. Try again."

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # Fetch weather using Open-Meteo
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        weather = weather_data.get("current_weather", {})
        temp = weather.get("temperature")
        wind = weather.get("windspeed")

        return f"🌤️ Weather in {location.title()}:\nTemperature: {temp}°C\nWind Speed: {wind} km/h"
    except Exception as e:
        print("Weather error:", e)
        return "❌ Failed to fetch weather."
