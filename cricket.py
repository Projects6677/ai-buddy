# cricket.py
import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")

def get_live_match_list():
    """Fetches a list of all currently live cricket matches."""
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "API_ERROR"

    url = f"https://{RAPIDAPI_HOST}/matches/v1/live"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        live_matches = []
        if data.get("typeMatches"):
            for match_type in data["typeMatches"]:
                for series_match in match_type.get("seriesMatches", []):
                    ad_wrapper = series_match.get("seriesAdWrapper")
                    if ad_wrapper and ad_wrapper.get("matches"):
                        for match in ad_wrapper["matches"]:
                            info = match.get("matchInfo", {})
                            if info.get("state") == "In Progress":
                                match_data = {
                                    "id": info.get("matchId"),
                                    "description": f"{info.get('team1', {}).get('teamName', 'T1')} vs {info.get('team2', {}).get('teamName', 'T2')}",
                                    "series": info.get("seriesName", "N/A")
                                }
                                live_matches.append(match_data)
        
        return live_matches

    except Exception as e:
        print(f"Cricket API Error (get_live_match_list): {e}")
        return "API_ERROR"

def get_score_for_match(match_id):
    """Fetches the detailed score for a single match ID."""
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ The Cricket API key or host is not configured."
    
    url = f"https://{RAPIDAPI_HOST}/matches/v1/getScorecard"
    params = {"matchId": str(match_id)}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        info = data.get("matchInfo", {})
        score = data.get("scoreCard", [])[0] if data.get("scoreCard") else {}
        
        team1_info = info.get("team1", {})
        team2_info = info.get("team2", {})
        
        team1_score = score.get("team1Score", {}).get("inngs1", {})
        team2_score = score.get("team2Score", {}).get("inngs1", {})

        return (
            f"🏏 *{team1_info.get('teamName', 'Team 1')} vs {team2_info.get('teamName', 'Team 2')}*\n"
            f"_{info.get('matchDesc', '')}, {info.get('venueInfo', {}).get('city', '')}_\n\n"
            f"*{team1_info.get('teamName', 'Team 1')}:* {team1_score.get('runs', 0)}/{team1_score.get('wickets', 0)} ({team1_score.get('overs', 0)} ov)\n"
            f"*{team2_info.get('teamName', 'Team 2')}:* {team2_score.get('runs', 0)}/{team2_score.get('wickets', 0)} ({team2_score.get('overs', 0)} ov)\n\n"
            f"Status: _{info.get('status', 'No status available')}_"
        )
    except Exception as e:
        print(f"Cricket API Error (get_score_for_match): {e}")
        return "❌ Sorry, I couldn't fetch the score for that specific match."
