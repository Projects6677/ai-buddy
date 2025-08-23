# youtube_search.py

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def search_youtube_for_video(credentials, query):
    """
    Searches YouTube for a video based on a query and returns the top result.
    """
    try:
        # Build the YouTube API service object
        youtube_service = build('youtube', 'v3', credentials=credentials)

        # Call the search.list method to retrieve results
        search_response = youtube_service.search().list(
            q=query,
            part='snippet',
            maxResults=1,  # We only need the top result
            type='video'
        ).execute()

        results = search_response.get('items', [])

        if not results:
            return f"😕 Sorry, I couldn't find any videos matching your search for '*{query}*'."

        # Extract the video ID and title from the top result
        top_result = results[0]
        video_id = top_result['id']['videoId']
        video_title = top_result['snippet']['title']
        
        # Construct the full YouTube URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        response_message = (
            f"🔎 Here is the top result for '*{query}*':\n\n"
            f"🎬 *{video_title}*\n"
            f"🔗 {video_url}"
        )
        
        return response_message

    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        # Check for a quota error specifically
        if e.resp.status == 403:
            return "❌ Could not perform the YouTube search. The API quota may have been exceeded."
        return "❌ An error occurred while searching YouTube."
    except Exception as e:
        print(f"An unexpected error occurred during YouTube search: {e}")
        return "❌ An unexpected error occurred while searching YouTube."
