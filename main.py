import os
import random
import json
import subprocess
import requests
import yt_dlp
from pathlib import Path
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from instagrapi import Client

# -- Config --
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
DOWNLOAD_DIR = Path("downloads")
POSTED_LOG   = Path("posted.json")

DOWNLOAD_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SUBREDDITS = ["dankmemes", "memes", "funny", "me_irl", "shitposting", "funnymemes", "unexpected"]
CAPTIONS = ["💀 tag someone! #memevideo #viral #memeaholicdaily", "bro why 😭 #funny #reels", "the ending lol #shorts #memes"]

def load_posted():
    if POSTED_LOG.exists():
        try: return set(json.loads(POSTED_LOG.read_text()))
        except: return set()
    return set()

def save_posted(posted):
    POSTED_LOG.write_text(json.dumps(list(posted)))

def download_yt_short(posted):
    """Tries to find a viral YouTube Short using yt-dlp"""
    search_query = "ytsearch5:trending memes shorts"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(DOWNLOAD_DIR / 'yt_%(id)s.mp4'),
        'quiet': True,
        'noplaylist': True,
        'match_filter': yt_dlp.utils.match_filter_func("duration < 60"),
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            for entry in info['entries']:
                if entry['id'] not in posted:
                    ydl.download([entry['webpage_url']])
                    return DOWNLOAD_DIR / f"yt_{entry['id']}.mp4", entry['id']
    except Exception as e:
        print(f"YouTube Error: {e}")
    return None, None

def get_reddit_videos(posted):
    random.shuffle(SUBREDDITS)
    for sub in SUBREDDITS[:5]:
        try:
            # Check 'hot' instead of 'top' for fresher content
            r = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=30", headers=HEADERS, timeout=15)
            if r.status_code != 200: continue
            
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                d = post["data"]
                if d["id"] in posted: continue
                if d.get("is_video") and d.get("media"):
                    v_url = d["media"]["reddit_video"]["fallback_url"].split("?")[0]
                    out = DOWNLOAD_DIR / f"red_{d['id']}.mp4"
                    dl = requests.get(v_url, headers=HEADERS, timeout=30)
                    if dl.status_code == 200:
                        out.write_bytes(dl.content)
                        return out, d["id"]
        except: continue
    return None, None

def post_reel(video_path, caption):
    cl = Client()
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.clip_upload(video_path, caption)
    print(f"✅ Posted {video_path.name}")

def run():
    posted = load_posted()
    print("🤖 Searching for candidates...")
    
    # Try YouTube first, then fall back to Reddit
    video_path, vid_id = download_yt_short(posted)
    
    if not video_path:
        print("Falling back to Reddit...")
        video_path, vid_id = get_reddit_videos(posted)

    if video_path and video_path.exists():
        try:
            post_reel(video_path, random.choice(CAPTIONS))
            posted.add(vid_id)
            save_posted(posted)
        except Exception as e:
            print(f"Post failed: {e}")
    else:
        print("❌ Still no candidates found.")

if __name__ == "__main__":
    run()
