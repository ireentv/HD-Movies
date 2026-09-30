#!/usr/bin/env python3
"""
IreenTV HD Movies - Auto Updater Script
Automatically fetches latest Hindi & South movies and updates 'HD Movies.m3u'
"""

import os
import re
import json
import urllib.request
import urllib.error

OUTPUT_FILE = "HD Movies.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# MX Player / Public Video Catalogs (Free Content API)
CATALOG_API_ENDPOINTS = [
    {
        "url": "https://api.mxplayer.in/v1/web/home/tab/movies?device-density=2&platform=com.mxplay.desktop&content-languages=hi,te,ta",
        "category": "Bollywood"
    },
    {
        "url": "https://api.mxplayer.in/v1/web/detail/browse/movie?filter=language:hindi&page=1&limit=40&device-density=2&platform=com.mxplay.desktop",
        "category": "Bollywood"
    },
    {
        "url": "https://api.mxplayer.in/v1/web/detail/browse/movie?filter=language:telugu,tamil&page=1&limit=40&device-density=2&platform=com.mxplay.desktop",
        "category": "South Dubbed"
    }
]

def make_request(url):
    """Safely fetch JSON from an API endpoint with custom headers."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://www.mxplayer.in/"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                return json.loads(data)
    except Exception as e:
        print(f"[-] Notice: Could not fetch from {url} ({e})")
    return None

def parse_existing_m3u(file_path):
    """Read existing movies so we do not duplicate or lose any existing entries."""
    existing_movies = {}
    if not os.path.exists(file_path):
        return existing_movies

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_info = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#EXTINF:"):
                current_info = line
            elif line.startswith("http") and current_info:
                # Extract clean title from #EXTINF
                parts = current_info.split(",")
                title = parts[-1].strip() if len(parts) > 1 else "Unknown"
                clean_key = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
                existing_movies[clean_key] = {
                    "info": current_info,
                    "url": line,
                    "title": title
                }
                current_info = None
    except Exception as e:
        print(f"[-] Error reading existing M3U: {e}")

    return existing_movies

def clean_movie_title(raw_title):
    """Remove unwanted year, tags, brackets for clean display."""
    title = re.sub(r'\(.*?\)|\[.*?\]', '', raw_title)
    title = re.sub(r'\b(Hindi|Dubbed|Full Movie|HD|1080p|720p)\b', '', title, flags=re.IGNORECASE)
    return title.strip()

def fetch_fresh_movies():
    """Scrape and parse available movies from streaming API feeds."""
    new_items = []
    
    for endpoint in CATALOG_API_ENDPOINTS:
        url = endpoint["url"]
        default_cat = endpoint["category"]
        print(f"[+] Scanning feed: {default_cat} ...")

        res = make_request(url)
        if not res:
            continue

        items = []
        if "items" in res and isinstance(res["items"], list):
            items = res["items"]
        elif "sections" in res and isinstance(res["sections"], list):
            for sec in res["sections"]:
                if "items" in sec and isinstance(sec["items"], list):
                    items.extend(sec["items"])

        for item in items:
            title = item.get("title") or item.get("name")
            if not title:
                continue

            # Determine poster image
            image_path = item.get("imageInfo", [{}])[0].get("url") if item.get("imageInfo") else None
            if not image_path:
                image_path = item.get("imageUrl") or item.get("thumbnail")
            
            poster = f"https://qqcdnpictest.mxplay.com/{image_path}" if image_path and not image_path.startswith("http") else (image_path or "")

            # Check stream URL or HLS
            stream_url = item.get("streamUrl") or item.get("hlsUrl") or item.get("videoUrl")
            
            # If item has nested streamProvider / cdnUrl:
            if not stream_url and "stream" in item:
                stream_url = item["stream"].get("hls", {}).get("high")

            if title and stream_url:
                clean_title = clean_movie_title(title)
                new_items.append({
                    "title": clean_title,
                    "logo": poster,
                    "stream": stream_url,
                    "category": default_cat
                })

    return new_items

def update_playlist():
    """Merge new movies into HD Movies.m3u without duplicating."""
    print("=" * 60)
    print("🎬 IreenTV Movie Catalog Auto-Updater Starting...")
    print("=" * 60)

    existing = parse_existing_m3u(OUTPUT_FILE)
    print(f"[✓] Existing movies in catalog: {len(existing)}")

    fresh_movies = fetch_fresh_movies()
    print(f"[✓] Discovered candidate movies from feeds: {len(fresh_movies)}")

    added_count = 0
    for movie in fresh_movies:
        key = re.sub(r'[^a-zA-Z0-9]', '', movie["title"]).lower()
        if key not in existing and len(movie["title"]) > 1:
            info_line = f'#EXTINF:-1 tvg-logo="{movie["logo"]}" group-title="{movie["category"]}",{movie["title"]}'
            existing[key] = {
                "info": info_line,
                "url": movie["stream"],
                "title": movie["title"]
            }
            added_count += 1

    # Write out the updated M3U file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for key, entry in existing.items():
            f.write(f'{entry["info"]}\n')
            f.write(f'{entry["url"]}\n')

    print("=" * 60)
    print(f"🎉 Successfully updated '{OUTPUT_FILE}'!")
    print(f"   - Total movies now: {len(existing)}")
    print(f"   - New movies added today: {added_count}")
    print("=" * 60)

if __name__ == "__main__":
    update_playlist()
