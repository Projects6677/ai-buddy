# cricket.py
import requests
import json
import os
import time

CRICAPI_URL = "https://api.cricapi.com/v1"
API_KEY = "TESTKEY0273"  # Use for development. Get your own key by signing up on cricapi.com

def get_matches_from_api():
    """
    Fetches all available cricket matches from CricAPI.
    """
    url = f"{CRICAPI_URL}/matches?apikey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"CricAPI match list error: {e}")
        return None

def get_match_score(match_id):
    """
    Fetches the score for a specific match ID from CricAPI.
    """
    url = f"{CRICAPI_URL}/matchscore?apikey={API_KEY}&id={match_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
    except requests.exceptions.RequestException as e:
        print(f"CricAPI match score error: {e}")
        return None

def format_score_response(match_data):
    """
    Formats the match data into a readable string.
    """
    if not match_data:
        return "❌ An unexpected error occurred. Please try again later."
    
    match_name = match_data.get("name", "Match")
    match_status = match_data.get("status", "Status not available")
    
    response_text = f"🏏 *Match: {match_name}*\n\n"
    
    for inning in match_data.get("scorecard", []):
        team = inning.get("inning", "N/A")
        score_text = ""
        for score in inning.get("score", []):
            score_text += f"{score.get('r')}/{score.get('w')} ({score.get('o')} Overs)\n"
        
        response_text += f"*{team}*: {score_text}\n"

    response_text += f"\n_Status: {match_status}_"
    return response_text
