import os
import random
import yt_dlp
from pathlib import Path

# ... (keep your existing imports and config) ...

def download_universal(url, post_id):
    out_path = DOWNLOAD_DIR / f"vid_{post_id}.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(out_path),
        'quiet': True,
        'noplaylist': True,
        # This helps bypass some bot detection
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out_path if out_path.exists() else None
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None

# New Source List
SOURCES = [
    "https://www.reddit.com/r/shitposting/hot.json",
    "https://www.youtube.com/hashtag/shorts/videos",
    "https://www.tiktok.com/tag/memes"
]

# Note: TikTok and IG are VERY hard to scrape without an API key or a "Headless Browser".
# For a GitHub Action, YouTube Shorts and Reddit are the most reliable.
