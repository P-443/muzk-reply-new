import os

from yt_dlp import YoutubeDL

# Cookies are an OPT-IN fallback via YTDLP_COOKIES=/path/cookies.txt. On a
# datacenter IP, YouTube rejects a cookie session with "Sign in to confirm
# you're not a bot", so the default path is the bgutil PO-token provider
# (designed for datacenter IPs) which runs automatically in the container.
# A residential proxy for the yt-dlp requests is the most reliable fix for a
# hard-flagged datacenter IP: set YTDLP_PROXY=https://user:pass@host:port.
_COOKIES = os.getenv("YTDLP_COOKIES")
_PROXY = os.getenv("YTDLP_PROXY")

ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "geo_bypass": True,
    "nocheckcertificate": True,
    # Enable Node.js as the JS runtime for yt-dlp. The container ships Node
    # (no deno), and the web player's "n" challenge + PO-token flow need a JS
    # runtime to avoid YouTube's datacenter-IP bot-check.
    "js_runtimes": {"node": {}},
    "quiet": True,
    "no_warnings": True,
    "prefer_ffmpeg": True,
    "retries": 10,
    "fragment_retries": 10,
    "extractor_retries": 3,
    # yt-dlp tries clients in REVERSE config order, falling through on
    # bot-check. "web" is last on purpose: bgutil PO token is only generated
    # when web (or another PO-token client) is actually used. android/ios are
    # YouTube's mobile API and are frequently the ones that pass a bot-checked
    # datacenter IP, so they are tried first.
    "extractor_args": {
        "youtube": {
            "player_client": [
                "web", "visionos", "tv_downgraded", "tv", "web_embedded",
                "android", "ios", "mweb",
            ],
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

if _COOKIES and os.path.exists(_COOKIES):
    ydl_opts["cookiefile"] = _COOKIES
if _PROXY:
    ydl_opts["proxy"] = _PROXY

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