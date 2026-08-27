import os

from yt_dlp import YoutubeDL

# Optional: cookies to bypass YouTube's bot-check on datacenter IPs.
# Drop a "cookies.txt" in the repo root, or set YTDLP_COOKIES=/path/cookies.txt
# (the bot still runs without it, just with more download failures).
_COOKIES = os.getenv("YTDLP_COOKIES")

ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "quiet": True,
    "no_warnings": True,
    "prefer_ffmpeg": True,
    "retries": 10,
    "fragment_retries": 10,
    "extractor_retries": 3,
    "extractor_args": {
        "youtube": {
            "player_client": ["visionos", "tv_downgraded", "tv", "web_embedded"],
        }
    },
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }
    ],
}

if not _COOKIES and os.path.exists("cookies.txt"):
    _COOKIES = "cookies.txt"

if _COOKIES and os.path.exists(_COOKIES):
    ydl_opts["cookiefile"] = _COOKIES
    # With cookies, prefer the normal web client (best formats) and keep the
    # no-auth clients as fallback.
    ydl_opts["extractor_args"]["youtube"]["player_client"] = [
        "web",
        "visionos",
        "tv",
        "web_embedded",
    ]

ydl = YoutubeDL(ydl_opts)


def audio_dl(url: str) -> str:
    sin = ydl.extract_info(url, False)
    x_file = os.path.join("downloads", f"{sin['id']}.mp3")
    if os.path.exists(x_file):
        return x_file
    ydl.download([url])
    return x_file