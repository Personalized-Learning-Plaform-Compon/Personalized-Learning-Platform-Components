import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Ensure that the environment variables are set
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

def fetch_youtube_videos(topic):
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={topic}&type=video&maxResults=5&key={YOUTUBE_API_KEY}"
    response = requests.get(search_url)
    if response.status_code == 200:
        videos = response.json().get("items", [])
        return [{"title": vid["snippet"]["title"], "url": f"https://www.youtube.com/watch?v={vid['id']['videoId']}"} for vid in videos]
    return []

def fetch_google_sites(topic):
    search_url = f"https://www.googleapis.com/customsearch/v1?q={topic}&key={YOUTUBE_API_KEY}&cx={SEARCH_ENGINE_ID}"
    response = requests.get(search_url)
    if response.status_code == 200:
        sites = response.json().get("items", [])
        return [{"title": site["title"], "url": site["link"]} for site in sites]
    return []





