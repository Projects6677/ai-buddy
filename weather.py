# weather.py
import requests
import os
from grok_ai import generate_weather_summary # Import the new AI function

def get_weather(location):
    """
    Fetches detailed weather data for a location and uses AI to generate a summary.
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return "❌ The weather service is not configured by the administrator."

    try:
        # Use OpenWeatherMap's Geocoding API to get lat/lon for the location
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if not geo_data:
            return f"⚠️ I couldn't find the location '{location}'. Please try again with a different city name."

        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_name = geo_data[0]["name"]

        # Use the lat/lon to get the current weather data
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        # Pass the raw data to the AI for a descriptive summary
        detailed_summary = generate_weather_summary(weather_data, city_name)
        
        return detailed_summary

    except requests.exceptions.HTTPError as e:
        print(f"Weather API HTTP error for {location}: {e}")
        return "❌ Sorry, I couldn't connect to the weather service right now."
    except (IndexError, KeyError):
         return f"⚠️ I couldn't find the location '{location}'. Please be more specific."
    except Exception as e:
        print(f"An unexpected weather error occurred for {location}: {e}")
        return "❌ An unexpected error occurred while fetching the weather."
