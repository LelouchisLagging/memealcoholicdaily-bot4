import os
import random
import json
import subprocess
import requests
import time
from pathlib import Path
from datetime import datetime

from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from instagrapi import Client

IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")

DOWNLOAD_DIR = Path("downloads")
BRANDED_DIR  = Path("branded")
POSTED_LOG   = Path("posted.json")

DOWNLOAD_DIR.mkdir(exist_ok=True)
BRANDED_DIR.mkdir(exist_ok=True)

SUBREDDITS = [
    "dankmemes", "memes", "funny", "shitposting",
    "perfectlycutscreams", "unexpected", "maybemaybemaybe",
    "funnymemes", "me_irl", "okbuddyretard"
]

CAPTIONS = [
    "💀 tag someone who needs to see this\n\n#memevideo #funnymemes #dankmemes #viral #reels #memeaholicdaily #fyp #humor #lol #trending",
    "this one got me 😭😭\n\n#memevideo #dankmemes #funny #viral #reels #foryou #memeaholicdaily #relatable #fyp",
    "not me dying rn 💀\n\n#memevideo #funny #viral #reels #foryoupage #memeaholicdaily #trending #lol #humor #fyp",
    "bro why is this so accurate 😭\n\n#memevideo #relatable #funny #viral #reels #memeaholicdaily #foryou #humor #trending #fyp",
    "send this to your group chat 🚀\n\n#memevideo #funny #humor #viral #reels #memeaholicdaily #foryou #fyp #trending #lol",
    "i cannot 💀💀💀\n\n#memevideo #funny #lol #viral #reels #memeaholicdaily #fyp #foryou #humor #trending",
    "the accuracy tho 😭\n\n#memevideo #relatable #funny #viral #fyp #memeaholicdaily #reels #humor #lol #foryou",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def load_posted():
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()))
    return set()

def save_posted(posted):
    POSTED_LOG.write_text(json.dumps(list(posted)))

def get_reddit_videos(posted):
    candidates = []
    random.shuffle(SUBREDDITS)
    for sub in SUBREDDITS[:6]:
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            session.get(f"https://old.reddit.com/r/{sub}/", timeout=10)
            time.sleep(1)
            url = f"https://old.reddit.com/r/{sub}/top.json?t=day&limit=25&raw_json=1"
            r = session.get(url, timeout=15)
            print(f"r/{sub} status: {r.status_code}")
            if r.status_code != 200:
                continue
            try:
                data = r.json()
            except Exception as e:
                print(f"r/{sub} JSON failed: {e}")
                continue
            posts = data["data"]["children"]
            for post in posts:
                d = post["data"]
                post_id = d["id"]
                if post_id in posted:
                    continue
                if d.get("is_video") and d.get("media"):
                    video_url = d["media"]["reddit_video"]["fallback_url"].split("?")[0]
                    audio_url = "/".join(video_url.split("/")[:-1]) + "/DASH_audio.mp4"
                    out = DOWNLOAD_DIR / f"reddit_{post_id}.mp4"
                    print(f"Downloading: {d.get('title', '')[:50]}")
                    dl = session.get(video_url, timeout=30, stream=True)
                    if dl.status_code == 200:
                        with open(out, "wb") as f:
                            for chunk in dl.iter_content(8192):
                                f.write(chunk)
                    audio_out = DOWNLOAD_DIR / f"audio_{post_id}.mp4"
                    try:
                        adl = session.get(audio_url, timeout=15, stream=True)
                        if adl.status_code == 200:
                            with open(audio_out, "wb") as f:
                                for chunk in adl.iter_content(8192):
                                    f.write(chunk)
                            merged = DOWNLOAD_DIR / f"merged_{post_id}.mp4"
                            subprocess.run([
                                "ffmpeg", "-y",
                                "-i", str(out), "-i", str(audio_out),
                                "-c:v", "copy", "-c:a", "aac",
                                str(merged)
                            ], capture_output=True, timeout=30)
                            if merged.exists() and merged.stat().st_size > 50000:
                                out.unlink(missing_ok=True)
                                audio_out.unlink(missing_ok=True)
                                out = merged
                    except Exception:
                        audio_out.unlink(missing_ok=True)
                    if out.exists() and out.stat().st_size > 50000:
                        try:
                            result = subprocess.run(
                                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(out)],
                                capture_output=True, text=True
                            )
                            duration = float(json.loads(result.stdout)["format"]["duration"])
                            if duration > 90:
                                out.unlink(missing_ok=True)
                                continue
                        except Exception:
                            pass
                        candidates.append((out, post_id))
                        print(f"Got video: {out.name}")
                        if len(candidates) >= 5:
                            return candidates
        except Exception as e:
            print(f"Error ({sub}): {e}")
    return candidates

def brand_video(input_path):
    out_path = BRANDED_DIR / f"branded_{input_path.name}"
    try:
        clip = VideoFileClip(str(input_path))
        watermark = (
            TextClip(
                "@memeaholicdaily",
                fontsize=max(16, int(clip.w * 0.042)),
                font="Liberation-Sans-Bold",
                color="white",
            )
            .set_opacity(0.32)
            .set_duration(clip.duration)
            .margin(top=16, right=16, opacity=0)
            .set_position(("right", "top"))
        )
        final = CompositeVideoClip([clip, watermark])
        final.write_videofile(
            str(out_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
            temp_audiofile="temp_audio.m4a",
            remove_temp=True,
        )
        clip.close()
        final.close()
        return out_path
    except Exception as e:
        print(f"Branding failed: {e}")
        return input_path

def post_reel(video_path, caption):
    cl = Client()
    session_file = Path("session.json")
    if session_file.exists():
        cl.load_settings(session_file)
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(session_file)
    cl.clip_upload(video_path, caption)
    print(f"Posted: {video_path.name} @ {datetime.now():%H:%M:%S}")

def run():
    posted = load_posted()
    print(f"Bot starting | {len(posted)} already posted")
    candidates = get_reddit_videos(posted)
    if not candidates:
        print("No new meme videos found this run.")
        return
    print(f"Found {len(candidates)} candidates")
    video_path, vid_id = random.choice(candidates)
    print(f"Selected: {video_path.name}")
    branded = brand_video(video_path)
    caption = random.choice(CAPTIONS)
    post_reel(branded, caption)
    posted.add(vid_id)
    save_posted(posted)
    for f in DOWNLOAD_DIR.glob("*.mp4"):
        f.unlink(missing_ok=True)
    branded.unlink(missing_ok=True)
    print("Run complete!")

if __name__ == "__main__":
    run()
