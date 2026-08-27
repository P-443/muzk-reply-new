
import os

from yt_dlp import YoutubeDL

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
    # Bypass YouTube "Sign in to confirm you're not a bot" without cookies:
    # use player clients that don't require login/PO tokens, in order of preference.
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
ydl = YoutubeDL(ydl_opts)


def audio_dl(url: str) -> str:
    sin = ydl.extract_info(url, False)
    x_file = os.path.join("downloads", f"{sin['id']}.mp3")
    if os.path.exists(x_file):
        return x_file
    ydl.download([url])
    return x_file
