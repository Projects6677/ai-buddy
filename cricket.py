# cricket.py
import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")

def get_live_scores():
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ The Cricket API key or host is not configured."

    # NOTE: This URL endpoint is for the Cricbuzz API on RapidAPI.
    # If you chose a different API, you may need to change the endpoint.
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
        
        # This parsing logic is specific to the Cricbuzz API.
        # You may need to adjust the keys if your API has a different structure.
        if data.get("typeMatches"):
            for match_type in data["typeMatches"]:
                for series_match in match_type.get("seriesMatches", []):
                    ad_wrapper = series_match.get("seriesAdWrapper")
                    if ad_wrapper and ad_wrapper.get("matches"):
                        for match in ad_wrapper["matches"]:
                            info = match.get("matchInfo", {})
                            score = match.get("matchScore", {})
                            
                            if info.get("state") == "In Progress":
                                team1_info = info.get("team1", {})
                                team2_info = info.get("team2", {})
                                team1_score = score.get("team1Score", {}).get("inngs1", {})
                                team2_score = score.get("team2Score", {}).get("inngs1", {})

                                match_str = (
                                    f"🏏 *{team1_info.get('teamName', 'Team 1')} vs {team2_info.get('teamName', 'Team 2')}*\n"
                                    f"_{info.get('matchDesc', '')}, {info.get('venueInfo', {}).get('city', '')}_\n\n"
                                    f"*{team1_info.get('teamName', 'Team 1')}:* {team1_score.get('runs', 0)}/{team1_score.get('wickets', 0)} ({team1_score.get('overs', 0)} ov)\n"
                                    f"*{team2_info.get('teamName', 'Team 2')}:* {team2_score.get('runs', 0)}/{team2_score.get('wickets', 0)} ({team2_score.get('overs', 0)} ov)\n\n"
                                    f"Status: _{info.get('status', 'No status available')}_"
                                )
                                live_matches.append(match_str)

        if not live_matches:
            return "No live cricket matches found at the moment. 🏏"

        return "\n\n---\n\n".join(live_matches)

    except Exception as e:
        print(f"Cricket API Error: {e}")
        return "❌ Sorry, I couldn't fetch live scores right now. Please check the API configuration."
