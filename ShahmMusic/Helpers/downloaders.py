import os

from yt_dlp import YoutubeDL

# Optional cookies.txt fallback (strongest guarantee against YouTube's
# datacenter bot-check). Drop a "cookies.txt" in the repo root, or set
# YTDLP_COOKIES=/path/cookies.txt. Not required: the bgutil PO-token provider
# is used automatically when the container runs it.
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
    # "web" goes first so the bgutil PO-token provider (or cookies) is used;
    # the rest are no-auth fallbacks in case web fails.
    "extractor_args": {
        "youtube": {
            "player_client": ["web", "visionos", "tv_downgraded", "tv", "web_embedded"],
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

ydl = YoutubeDL(ydl_opts)


def audio_dl(url: str) -> str:
    sin = ydl.extract_info(url, False)
    x_file = os.path.join("downloads", f"{sin['id']}.mp3")
    if os.path.exists(x_file):
        return x_file
    ydl.download([url])
    return x_file


def yt_search(query: str, max_results: int = 1):
    """Search YouTube via yt-dlp (reuses the same cookies/client config).

    Returns a list of dicts shaped like the legacy youtube_search lib:
    id, title, duration ("M:SS"), url_suffix, views, channel, thumbnails.
    """
    opts = dict(ydl_opts)
    opts.pop("postprocessors", None)
    opts["skip_download"] = True
    q = (query or "").strip()
    if q.startswith(("http://", "https://")):
        target = q
    else:
        target = f"ytsearch{max_results}:{q}"
    with YoutubeDL(opts) as search_ydl:
        info = search_ydl.extract_info(target, download=False)
    entries = [info] if "entries" not in info else (info.get("entries") or [])
    out = []
    for e in entries:
        if not e:
            continue
        dur = int(e.get("duration") or 0)
        out.append({
            "id": e.get("id"),
            "title": e.get("title") or "",
            "duration": f"{dur // 60}:{dur % 60:02d}",
            "url_suffix": "/watch?v=" + (e.get("id") or ""),
            "views": str(e.get("view_count") or ""),
            "channel": e.get("channel") or e.get("uploader") or "",
            "thumbnails": [
                t.get("url") for t in (e.get("thumbnails") or []) if t.get("url")
            ],
        })
    return out