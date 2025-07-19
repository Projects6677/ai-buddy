import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")

def get_combined_matches():
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return {"error": "❌ The Cricket API key or host is not configured."}

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    combined_matches = {"live": [], "upcoming": []}
    seen_descriptions = set()

    try:
        # Fetch both live and upcoming matches
        live_url = f"https://{RAPIDAPI_HOST}/matches/v1/live"
        upcoming_url = f"https://{RAPIDAPI_HOST}/matches/v1/upcoming"

        for url, category in [(live_url, "live"), (upcoming_url, "upcoming")]:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("typeMatches"):
                for match_type in data["typeMatches"]:
                    for series_match in match_type.get("seriesMatches", []):
                        ad_wrapper = series_match.get("seriesAdWrapper")
                        if ad_wrapper and ad_wrapper.get("matches"):
                            for match in ad_wrapper["matches"]:
                                info = match.get("matchInfo", {})
                                team1_name = info.get('team1', {}).get('teamName', 'TBC')
                                team2_name = info.get('team2', {}).get('teamName', 'TBC')
                                
                                if "TBC" in team1_name or "TBC" in team2_name:
                                    continue # Skip matches with TBC teams

                                description = f"{team1_name} vs {team2_name}"
                                if description in seen_descriptions:
                                    continue # Skip duplicate matches
                                
                                seen_descriptions.add(description)

                                if info.get("state") == "In Progress" and category == "live":
                                    combined_matches["live"].append({
                                        "id": info.get("matchId"),
                                        "description": description,
                                        "series": info.get("seriesName", "N/A")
                                    })
                                elif info.get("state") == "Upcoming" and category == "upcoming":
                                    combined_matches["upcoming"].append({
                                        "id": info.get("matchId"),
                                        "description": description,
                                        "series": info.get("seriesName", "N/A"),
                                    })
        
        # Limit the number of upcoming matches shown
        combined_matches["upcoming"] = combined_matches["upcoming"][:10]

        return combined_matches

    except Exception as e:
        print(f"Cricket API Error (get_combined_matches): {e}")
        return {"error": "❌ Sorry, I couldn't fetch match data right now."}

def get_score_for_match(match_id):
    # This function remains the same
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ The Cricket API key or host is not configured."
    
    url = f"https://{RAPIDAPI_HOST}/matches/v1/getScorecard"
    params = {"matchId": str(match_id)}
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}

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
            f"🏏 *{team1_info.get('teamName', 'T1')} vs {team2_info.get('teamName', 'T2')}*\n"
            f"_{info.get('matchDesc', '')}, {info.get('venueInfo', {}).get('city', '')}_\n\n"
            f"*{team1_info.get('teamName', 'T1')}:* {team1_score.get('runs', 0)}/{team1_score.get('wickets', 0)} ({team1_score.get('overs', 0)} ov)\n"
            f"*{team2_info.get('teamName', 'T2')}:* {team2_score.get('runs', 0)}/{team2_score.get('wickets', 0)} ({team2_score.get('overs', 0)} ov)\n\n"
            f"Status: _{info.get('status', 'No status available')}_"
        )
    except Exception as e:
        print(f"Cricket API Error (get_score_for_match): {e}")
        return "❌ Sorry, I couldn't fetch the score for that specific match."
