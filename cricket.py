# cricket.py
import os
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")

def get_live_match_list():
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
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        return "❌ The Cricket API key or host is not configured."
    
    url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

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

        # Batters and Bowlers
        batsmen_info = ""
        bowlers_info = ""
        
        # This will get the most recent innings data
        if score_card:
            latest_innings = score_card[-1]
            for batsman in latest_innings.get("batTeamDetails", {}).get("batsmenData", {}):
                if batsman.get("batStrike"):
                    batsmen_info += f"_{batsman.get('batName', '')}*: {batsman.get('runs', 0)} ({batsman.get('balls', 0)})\n"
            
            for bowler in latest_innings.get("bowlTeamDetails", {}).get("bowlersData", {}):
                 if bowler.get("bowlStrike"):
                     bowlers_info += f"_{bowler.get('bowlName', '')}*: {bowler.get('runsConceded', 0)}/{bowler.get('wickets', 0)} ({bowler.get('overs', 0)})\n"

        # Format score for the first innings
        if len(score_card) > 0:
            inng1_data = score_card[0]
            team1_name = inng1_data.get("batTeamName", team1.get("name", "Team 1"))
            score_line1 = f"*{team1_name}:* {inng1_data.get('runsScored', 0)}/{inng1_data.get('wickets', 0)} ({inng1_data.get('overs', 0)} ov)"

        # Format score for the second innings if it exists
        if len(score_card) > 1:
            inng2_data = score_card[1]
            team2_name = inng2_data.get("batTeamName", team2.get("name", "Team 2"))
            score_line2 = f"\n*{team2_name}:* {inng2_data.get('runsScored', 0)}/{inng2_data.get('wickets', 0)} ({inng2_data.get('overs', 0)} ov)"

        return (
            f"🏏 *{team1.get('name', 'T1')} vs {team2.get('name', 'T2')}*\n"
            f"_{header.get('matchDescription', '')}_\n\n"
            f"{score_line1}{score_line2}\n\n"
            f"*Batting:*\n{batsmen_info}\n"
            f"*Bowling:*\n{bowlers_info}\n"
            f"Status: _{status}_"
        )
    except Exception as e:
        print(f"Cricket API Error (get_score_for_match): {e}")
        return "❌ Sorry, I couldn't fetch the score for that specific match."
