# cricket.py
import requests
import json
import os
import time

def get_live_cricket_score():
    """
    Fetches a live cricket score from a mock API.
    In a real-world scenario, this would be replaced with a live sports API.
    """
    
    # In a real application, you would make an API call like this:
    # try:
    #     api_key = os.getenv("CRICKET_API_KEY")
    #     url = f"https://api.cricket-api.com/v1/live?apikey={api_key}"
    #     response = requests.get(url, timeout=10)
    #     response.raise_for_status()
    #     data = response.json()
    # except Exception as e:
    #     print(f"Cricket API error: {e}")
    #     return "❌ Failed to fetch live cricket scores."

    # --- MOCK DATA FOR DEMONSTRATION ---
    mock_data = {
        "status": "ok",
        "data": {
            "title": "India vs Australia - 2nd Test",
            "match_status": "in progress",
            "teams": ["India", "Australia"],
            "current_inning": "Australia",
            "score_card": {
                "India": {"runs": 245, "wickets": 4, "overs": 40.2},
                "Australia": {"runs": 120, "wickets": 10, "overs": 35.0}
            },
            "last_wicket": "Steve Smith, 12 runs"
        }
    }
    # --- END MOCK DATA ---

    try:
        data = mock_data.get("data", {})
        title = data.get("title")
        current_inning = data.get("current_inning")
        score_card = data.get("score_card", {})
        
        if not title or not score_card:
            return "❌ No live cricket match found at the moment."
            
        team1, team2 = data["teams"]
        score1 = score_card.get(team1)
        score2 = score_card.get(team2)
        
        response = f"🏏 *Live Cricket Score: {title}*\n\n"
        if score1:
            response += f"*{team1}*: {score1['runs']}/{score1['wickets']} ({score1['overs']} overs)\n"
        if score2:
            response += f"*{team2}*: {score2['runs']}/{score2['wickets']} ({score2['overs']} overs)\n"
        
        response += f"\n_Currently batting: {current_inning}_"

        return response

    except Exception as e:
        print(f"Error processing cricket data: {e}")
        return "❌ An unexpected error occurred while fetching cricket scores."
