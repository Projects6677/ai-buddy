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

        # Find the first ongoing match. If none, find the most recent completed match.
        target_match = None
        for m in data:
            if m.get("match_status") == "in progress":
                target_match = m
                break
        
        if not target_match and data:
            # Sort by date to get the most recent completed match
            data.sort(key=lambda m: m.get("date_time", ""), reverse=True)
            for m in data:
                if m.get("match_status") == "completed":
                    target_match = m
                    break

        if not target_match:
            return "❌ No live or recently completed cricket matches found at the moment."
        
        match_title = target_match.get("title", "Live Match")
        
        team1_name = target_match.get("teams", {}).get("team1", {}).get("name")
        team2_name = target_match.get("teams", {}).get("team2", {}).get("name")
        
        team1_score = target_match.get("teams", {}).get("team1", {}).get("score", "N/A")
        team2_score = target_match.get("teams", {}).get("team2", {}).get("score", "N/A")
        
        match_status = target_match.get('match_status')
        
        if match_status == 'in progress':
            response_text = f"🏏 *Live Cricket Score: {match_title}*\n\n"
        elif match_status == 'completed':
            response_text = f"✅ *Completed Match: {match_title}*\n\n"
        else:
            response_text = f"🏏 *Match Update: {match_title}*\n\n"
            
        response_text += f"*{team1_name}*: {team1_score}\n"
        response_text += f"*{team2_name}*: {team2_score}\n"
        response_text += f"\n_Status: {match_status}_"
        
        return response_text

    except requests.exceptions.RequestException as e:
        print(f"RapidAPI request error: {e}")
        return "❌ Failed to fetch live cricket scores. Please check your API keys or connection."
    except Exception as e:
        print(f"Error processing cricket data: {e}")
        return "❌ An unexpected error occurred while fetching cricket scores."
