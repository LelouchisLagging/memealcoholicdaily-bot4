import os
import random
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from instagrapi import Client

# -- Config --
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
DOWNLOAD_DIR = Path("downloads")
BRANDED_DIR  = Path("branded")
POSTED_LOG   = Path("posted.json")

DOWNLOAD_DIR.mkdir(exist_ok=True)
BRANDED_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "python-requests/2.31.0", "Accept": "application/json"}
SUBREDDITS = ["dankmemes", "memes", "funny", "me_irl", "shitposting", "funnymemes"]
CAPTIONS = ["💀 tag someone! #memevideo #viral #memeaholicdaily", "bro why 😭 #funny #reels"]

def load_posted():
    if POSTED_LOG.exists():
        try: 
            return set(json.loads(POSTED_LOG.read_text()))
        except: 
            return set()
    return set()

def save_posted(posted):
    POSTED_LOG.write_text(json.dumps(list(posted)))

def get_reddit_videos(posted):
    candidates = []
    random.shuffle(SUBREDDITS)
    for sub in SUBREDDITS[:5]:
        try:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25"
            r = requests.get(url, headers=HEADERS, timeout=15)
            
            # --- FIXED INDENTATION ---
            if r.status_code == 429:
                print(f"Rate limited on r/{sub}")
                continue
            if r.status_code != 200:
                continue
            
            data = r.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                d = post["data"]
                if d["id"] in posted: 
                    continue
                if d.get("is_video") and d.get("media"):
                    v_url = d["media"]["reddit_video"]["fallback_url"].split("?")[0]
                    out = DOWNLOAD_DIR / f"vid_{d['id']}.mp4"
                    dl = requests.get(v_url, headers=HEADERS, timeout=30)
                    if dl.status_code == 200:
                        out.write_bytes(dl.content)
                        candidates.append((out, d["id"]))
                if len(candidates) >= 3: 
                    return candidates
        except Exception as e:
            print(f"Error fetching from {sub}: {e}")
    return candidates

def post_reel(video_path, caption):
    cl = Client()
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.clip_upload(video_path, caption)
    print(f"✅ Posted {video_path.name}")

def run():
    posted = load_posted()
    candidates = get_reddit_videos(posted)
    if not candidates: 
        print("No candidates found.")
        return
    video_path, vid_id = random.choice(candidates)
    try:
        post_reel(video_path, random.choice(CAPTIONS))
        posted.add(vid_id)
        save_posted(posted)
    except Exception as e:
        print(f"Post failed: {e}")

if __name__ == "__main__":
    run()
