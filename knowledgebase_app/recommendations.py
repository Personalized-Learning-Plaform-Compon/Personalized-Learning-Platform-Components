import requests

YOUTUBE_API_KEY = "AIzaSyD7a_CHfuD97Feq7viloGSGVSAvkbs3B-4"
SEARCH_ENGINE_ID = '84c73da0137314611'

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





print(fetch_google_sites("what is oop"))