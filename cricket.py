# cricket.py
import requests
import json
import os
import time

CRICAPI_URL = "https://api.cricapi.com/v1"
API_KEY = os.getenv("CRICAPI_KEY")

def get_matches_from_api():
    """
    Fetches all available cricket matches from CricAPI.
    """
    if not API_KEY:
        print("❌ Error: CRICAPI_KEY is not configured.")
        return None

    url = f"{CRICAPI_URL}/currentMatches?apikey={API_KEY}&offset=0"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"CricAPI match list error: {e}")
        return None
    except json.decoder.JSONDecodeError:
        print("❌ Error: Invalid JSON response from CricAPI.")
        return None

def get_match_score(match_id):
    """
    Fetches the score for a specific match ID from CricAPI.
    """
    if not API_KEY:
        print("❌ Error: CRICAPI_KEY is not configured.")
        return None

    url = f"{CRICAPI_URL}/cricScore?apikey={API_KEY}&id={match_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
    except requests.exceptions.RequestException as e:
        print(f"CricAPI match score error: {e}")
        return None
    except json.decoder.JSONDecodeError:
        print("❌ Error: Invalid JSON response from CricAPI.")
        return None

def format_score_response(match_data):
    """
    Formats the match data into a readable string with more robust checks.
    """
    if not match_data:
        return "❌ An unexpected error occurred. Please try again later."
    
    # Check for missing match status
    match_status = match_data.get("status")
    if not match_status:
        # Provide a more specific message if score data is missing
        return "❌ Match data is currently unavailable. It may have been canceled or not started yet."
    
    match_name = match_data.get("name", "Match")
    
    response_text = f"🏏 *Match: {match_name}*\n\n"
    
    score = match_data.get("score", [])
    if score:
        for inning in score:
            team = inning.get("inning", "N/A")
            # Defensive check for score keys to prevent errors
            runs = inning.get("r", "N/A")
            wickets = inning.get("w", "N/A")
            overs = inning.get("o", "N/A")
            score_text = f"{runs}/{wickets} ({overs} Overs)"
            response_text += f"*{team}*: {score_text}\n"

    response_text += f"\n_Status: {match_status}_"
    return response_text
