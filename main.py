import os
import random
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from instagrapi import Client

IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY")

DOWNLOAD_DIR = Path("downloads")
BRANDED_DIR = Path("branded")
POSTED_LOG = Path("posted.json")
DOWNLOAD_DIR.mkdir(exist_ok=True)
BRANDED_DIR.mkdir(exist_ok=True)

CAPTIONS = [
    "💀 tag someone who needs to see this\n\n#memevideo #funnymemes #dankmemes #viral #reels #memeaholicdaily #fyp #humor #lol #trending",
    "this one got me 😭😭\n\n#memevideo #dankmemes #funny #viral #reels #foryou #memeaholicdaily #relatable #fyp",
    "not me dying rn 💀\n\n#memevideo #funny #viral #reels #foryoupage #memeaholicdaily #trending #lol #humor #fyp",
    "bro why is this so accurate 😭\n\n#memevideo #relatable #funny #viral #reels #memeaholicdaily #foryou #humor #trending #fyp",
    "send this to your group chat 🚀\n\n#memevideo #funny #humor #viral #reels #memeaholicdaily #foryou #fyp #trending #lol",
    "i cannot 💀💀💀\n\n#memevideo #funny #lol #viral #reels #memeaholicdaily #fyp #foryou #humor #trending",
    "the accuracy tho 😭\n\n#memevideo #relatable #funny #viral #fyp #memeaholicdaily #reels #humor #lol #foryou",
]

SEARCH_TERMS = ["meme", "funny", "dank meme", "humor", "lol", "fail", "reaction"]

def load_posted():
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()))
    return set()

def save_posted(posted):
    POSTED_LOG.write_text(json.dumps(list(posted)))

def get_giphy_videos(posted):
    candidates = []
    term = random.choice(SEARCH_TERMS)
    try:
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={term}&limit=25&rating=pg-13"
        r = requests.get(url, timeout=15)
        data = r.json()["data"]
        random.shuffle(data)
        for item in data:
            gif_id = item["id"]
            if gif_id in posted:
                continue
            # Get MP4 version
            mp4_url = item["images"].get("original_mp4", {}).get("mp4")
            if not mp4_url:
                continue
            out = DOWNLOAD_DIR / f"giphy_{gif_id}.mp4"
            dl = requests.get(mp4_url, timeout=30, stream=True)
            if dl.status_code == 200:
                with open(out, "wb") as f:
                    for chunk in dl.iter_content(8192):
                        f.write(chunk)
            if out.exists() and out.stat().st_size > 50000:
                # Check duration
                try:
                    result = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(out)],
                        capture_output=True, text=True
                    )
                    duration = float(json.loads(result.stdout)["format"]["duration"])
                    if duration < 3:
                        out.unlink(missing_ok=True)
                        continue
                    # Loop short gifs to make them longer for Instagram
                    if duration < 10:
                        looped = DOWNLOAD_DIR / f"looped_{gif_id}.mp4"
                        loops = max(2, int(10 / duration) + 1)
                        subprocess.run([
                            "ffmpeg", "-y", "-stream_loop", str(loops),
                            "-i", str(out), "-c", "copy", str(looped)
                        ], capture_output=True, timeout=30)
                        if looped.exists() and looped.stat().st_size > 50000:
                            out.unlink(missing_ok=True)
                            out = looped
                except Exception as e:
                    print(f"Duration check failed: {e}")
                candidates.append((out, gif_id))
                print(f"Got gif: {out.name}")
                if len(candidates) >= 5:
                    break
    except Exception as e:
        print(f"Giphy error: {e}")
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
    candidates = get_giphy_videos(posted)
    if not candidates:
        print("No videos found.")
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
    print("Done!")

if __name__ == "__main__":
    run()
