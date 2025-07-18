import os
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL = "llama3-70b-8192" # A larger model is better for summarization
GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

def get_video_id(url):
    """Extracts the YouTube video ID from various URL formats."""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def summarize_youtube_video(video_url):
    """Fetches a YouTube transcript and returns an AI-powered summary."""
    if not GROK_API_KEY:
        return "❌ The Grok API key is not configured. This feature is disabled."

    video_id = get_video_id(video_url)
    if not video_id:
        return "⚠️ That doesn't look like a valid YouTube video link. Please try again."

    try:
        # Get the transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([d['text'] for d in transcript_list])
        
        # Limit transcript length to avoid exceeding API limits
        if len(transcript) > 15000:
            transcript = transcript[:15000]

        # Get the summary from Grok
        system_prompt = "You are an expert summarization assistant. Summarize the following video transcript into a few key bullet points, focusing on the main ideas and conclusions."
        
        payload = {
            "model": GROK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript:\n{transcript}"}
            ],
            "temperature": 0.5
        }

        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        res.raise_for_status()
        summary = res.json()["choices"][0]["message"]["content"].strip()
        
        return f"📝 *Video Summary:*\n\n{summary}"

    except Exception as e:
        print(f"YouTube Summarizer Error: {e}")
        return "❌ Sorry, I couldn't get a summary for that video. It might not have a transcript or could be a private video."
