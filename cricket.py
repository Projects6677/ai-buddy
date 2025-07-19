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

                                match_details = {
                                    "id": info.get("matchId"),
                                    "description": description,
                                    "series": info.get("seriesName", "N/A"),
                                }

                                if info.get("state") == "In Progress" and category == "live":
                                    combined_matches["live"].append(match_details)
                                elif info.get("state") == "Upcoming" and category == "upcoming":
                                    combined_matches["upcoming"].append(match_details)
        
        # Limit the number of upcoming matches shown
        combined_matches["upcoming"] = combined_matches["upcoming"][:10]

        return combined_matches

    except Exception as e:
        print(f"Cricket API Error (get_combined_matches): {e}")
        return {"error": "❌ Sorry, I couldn't fetch match data right now."}

def get_score_for_match(match_id):
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ The Cricket API key or host is not configured."
    
    url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
    headers = { "X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        header = data.get("matchHeader", {})
        team1 = header.get("team1", {})
        team2 = header.get("team2", {})
        status = header.get("status", "No status available")
        
        score_card = data.get("scoreCard", [])
        score_line1, score_line2 = "", ""

        if len(score_card) > 0:
            inng1_data = score_card[0]
            team1_name = inng1_data.get("batTeamName", team1.get("name", "Team 1"))
            score_line1 = f"*{team1_name}:* {inng1_data.get('runsScored', 0)}/{inng1_data.get('wickets', 0)} ({inng1_data.get('overs', 0)} ov)"

        if len(score_card) > 1:
            inng2_data = score_card[1]
            team2_name = inng2_data.get("batTeamName", team2.get("name", "Team 2"))
            score_line2 = f"\n*{team2_name}:* {inng2_data.get('runsScored', 0)}/{inng2_data.get('wickets', 0)} ({inng2_data.get('overs', 0)} ov)"

        return (
            f"🏏 *{team1.get('name', 'T1')} vs {team2.get('name', 'T2')}*\n"
            f"_{header.get('matchDescription', '')}_\n\n"
            f"{score_line1}{score_line2}\n\n"
            f"Status: _{status}_"
        )
    except Exception as e:
        print(f"Cricket API Error (get_score_for_match): {e}")
        return "❌ Sorry, I couldn't fetch the score for that specific match."
