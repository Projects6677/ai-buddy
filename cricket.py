# cricket.py
import requests
import json
import os
import time

def get_live_cricket_score():
    """
    Fetches a live cricket score from the RapidAPI 'Free Cricbuzz Cricket API'.
    """
    RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
    RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")

    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ Error: RapidAPI keys are not configured."

    url = "https://free-cricbuzz-cricket-api.p.rapidapi.com/matches"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        live_matches = [m for m in data if m.get("match_status") == "in progress"]

        if not live_matches:
            return "❌ No live cricket matches found at the moment."
        
        # Taking the first live match for the example
        match = live_matches[0]
        match_title = match.get("title", "Live Match")
        
        team1_name = match.get("teams", {}).get("team1", {}).get("name")
        team2_name = match.get("teams", {}).get("team2", {}).get("name")
        
        team1_score = match.get("teams", {}).get("team1", {}).get("score", "N/A")
        team2_score = match.get("teams", {}).get("team2", {}).get("score", "N/A")
        
        response_text = f"🏏 *Live Cricket Score: {match_title}*\n\n"
        response_text += f"*{team1_name}*: {team1_score}\n"
        response_text += f"*{team2_name}*: {team2_score}\n"
        response_text += f"\n_Status: {match.get('match_status')}_"

        return response_text

    except requests.exceptions.RequestException as e:
        print(f"RapidAPI request error: {e}")
        return "❌ Failed to fetch live cricket scores. Please check your API keys or connection."
    except Exception as e:
        print(f"Error processing cricket data: {e}")
        return "❌ An unexpected error occurred while fetching cricket scores."
