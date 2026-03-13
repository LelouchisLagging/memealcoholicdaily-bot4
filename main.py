def download_yt_short(posted):
    """Tries to find any viral meme short from a wider search"""
    # Expanded search query and increased limit to 15
    search_query = "ytsearch15:funny memes shorts #shorts" 
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(DOWNLOAD_DIR / 'yt_%(id)s.mp4'),
        'quiet': True,
        'noplaylist': True,
        # Increased limit to 90 seconds for Reels/Shorts
        'match_filter': yt_dlp.utils.match_filter_func("duration < 90"), 
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            for entry in info.get('entries', []):
                if not entry: continue
                if entry['id'] not in posted:
                    print(f"Found YT Short: {entry['title']}")
                    ydl.download([entry['webpage_url']])
                    return DOWNLOAD_DIR / f"yt_{entry['id']}.mp4", entry['id']
    except Exception as e:
        print(f"YouTube Error: {e}")
    return None, None

def get_reddit_videos(posted):
    # Added even more subreddits to ensure we hit a video
    EXTENDED_SUBS = SUBREDDITS + ["FunnyAnimals", "WatchPeopleDieInside", "Instant_Regret"]
    random.shuffle(EXTENDED_SUBS)
    
    for sub in EXTENDED_SUBS[:10]: # Check 10 subreddits instead of 5
        try:
            # Look at top of the WEEK to ensure high quality/existence
            r = requests.get(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=50", headers=HEADERS, timeout=15)
            if r.status_code != 200: continue
            
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                d = post["data"]
                if d["id"] in posted: continue
                # Relaxed checks to find more videos
                if d.get("is_video"):
                    v_url = d["media"]["reddit_video"]["fallback_url"].split("?")[0]
                    out = DOWNLOAD_DIR / f"red_{d['id']}.mp4"
                    dl = requests.get(v_url, headers=HEADERS, timeout=30)
                    if dl.status_code == 200:
                        out.write_bytes(dl.content)
                        print(f"Found Reddit Video in r/{sub}")
                        return out, d["id"]
        except: continue
    return None, None
