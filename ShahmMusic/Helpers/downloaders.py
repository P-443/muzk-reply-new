import asyncio
import concurrent.futures
import os
import re
import time

import requests
from yt_dlp import YoutubeDL

from ShahmMusic import LOGGER

# ── Cookie-less YouTube access ──────────────────────────────────────────────
# No cookies anywhere. On a datacenter IP, YouTube bot-checks the "web"
# player client, so we:
#   1. try the mobile/embedded clients first (android / ios / mweb / tv) —
#      they are NOT bot-checked the way "web" is, and need no PO-token;
#   2. only fall back to the "web" client (which the bgutil PO-token
#      provider serves from 127.0.0.1:4416, see Dockerfile).
# yt-dlp processes extractor_args player_client IN THE ORDER LISTED (the
# old "reverse order" comment was wrong for current yt-dlp versions).
#
# YTDLP_FETCHER_URL: when set, audio_dl downloads through a small "fetcher"
# service running on a residential-IP machine (ytdlp-fetcher/fetcher.py).
# That service resolves + converts the video with yt-dlp from a clean IP and
# streams the mp3 back, sidestepping the datacenter-IP bot-check entirely.
# YTDLP_PROXY: optional http(s) proxy for the yt-dlp requests.
_FETCHER_URL = os.getenv("YTDLP_FETCHER_URL")
_PROXY = os.getenv("YTDLP_PROXY")
# Optional requests-based Google account login -- the YouTube Android app's
# model (the "Google Play" login). yt-dlp signs into Google with plain HTTP
# requests (email + password, optional 2FA code): NO browser cookies, NO
# selenium. A LOGGED-IN request is trusted by YouTube and is NOT subject to
# the "Sign in to confirm you're not a bot" gate that anonymous requests hit
# from this datacenter IP. Set in Coolify (then redeploy):
#   YTDLP_USERNAME=<gmail>   YTDLP_PASSWORD=<password>   YTDLP_TWOFA=<2fa code>
_YOUTUBE_USERNAME = os.getenv("YTDLP_USERNAME")
_YOUTUBE_PASSWORD = os.getenv("YTDLP_PASSWORD")
_YOUTUBE_TWOFA = os.getenv("YTDLP_TWOFA")
# The fetcher tunnel is ephemeral and often dead; short-circuit it for a few
# minutes instead of waiting the DNS/HTTP timeout on every request.
_fetcher_dead_until = 0.0


def _fetcher_alive() -> bool:
    return bool(_FETCHER_URL) and time.time() >= _fetcher_dead_until

LOGGER.info(
    "downloaders: YTDLP_FETCHER_URL=%s YTDLP_PROXY=%s account-login=%s (cookie-less mode)",
    "SET" if _FETCHER_URL else "NOT SET",
    "SET" if _PROXY else "NOT SET",
    "ENABLED" if (_YOUTUBE_USERNAME and _YOUTUBE_PASSWORD) else "OFF",
)

_VID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")


def _video_id(url: str) -> str:
    m = _VID_RE.search(url or "")
    return m.group(1) if m else "song"


def _thumb(id_: str) -> str:
    return f"https://i.ytimg.com/vi/{id_}/hqdefault.jpg"


ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "geo_bypass": True,
    "geo_bypass_country": "US",  # matches the config that works from clean IPs
    "nocheckcertificate": True,
    # Enable Node.js as the JS runtime for yt-dlp (the container ships Node
    # 22). Needed for the "n" challenge + PO-token flow on the web client.
    "js_runtimes": {"node": {}},
    "quiet": True,
    "no_warnings": True,
    "prefer_ffmpeg": True,
    "retries": 10,
    "fragment_retries": 10,
    "extractor_retries": 3,
    # Mobile/embedded clients first (not bot-checked like "web"), web last
    # (web is served by the bgutil PO-token provider on the datacenter IP).
    "extractor_args": {
        "youtube": {
            "player_client": [
                "android", "ios", "mweb", "tv", "web_embedded",
                "tv_downgraded", "visionos", "web",
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

if _PROXY:
    ydl_opts["proxy"] = _PROXY

# Account login rides on the android client (listed first in player_client),
# which makes the innertube player API request authenticated + trusted.
if _YOUTUBE_USERNAME and _YOUTUBE_PASSWORD:
    ydl_opts["username"] = _YOUTUBE_USERNAME
    ydl_opts["password"] = _YOUTUBE_PASSWORD
    if _YOUTUBE_TWOFA:
        ydl_opts["twofactor"] = _YOUTUBE_TWOFA

ydl = YoutubeDL(ydl_opts)


def _audio_dl_via_fetcher(url: str) -> str:
    """Download audio through the residential-IP fetcher service.

    The fetcher resolves the video from a clean IP (where YouTube is not
    bot-checked), converts it to mp3, and streams the bytes back. The
    container just saves them, so it never touches the YouTube player API.
    """
    vid = _video_id(url)
    x_file = os.path.join("downloads", f"{vid}.mp3")
    if os.path.exists(x_file):
        return x_file
    resp = requests.get(
        f"{_FETCHER_URL}/get_audio", params={"url": url}, timeout=180, stream=True)
    resp.raise_for_status()
    os.makedirs("downloads", exist_ok=True)
    part = x_file + ".part"
    with open(part, "wb") as f:
        for chunk in resp.iter_content(65536):
            if chunk:
                f.write(chunk)
    os.replace(part, x_file)
    return x_file


def audio_dl(url: str) -> str:
    if _fetcher_alive():
        try:
            LOGGER.info(f"audio_dl: fetching via fetcher ({_FETCHER_URL})")
            return _audio_dl_via_fetcher(url)
        except Exception as e:
            global _fetcher_dead_until
            _fetcher_dead_until = time.time() + 300
            LOGGER.error(f"audio_dl: fetcher failed ({e!r}); re-trying fetcher in 5 min")
    try:
        sin = ydl.extract_info(url, False)
        x_file = os.path.join("downloads", f"{sin['id']}.mp3")
        if os.path.exists(x_file):
            return x_file
        ydl.download([url])
        return x_file
    except Exception as e:
        # The datacenter IP is hard bot-checked, so the container's own yt-dlp
        # cannot download. Raise a clean, actionable error instead of letting
        # a raw DownloadError crash the handler.
        raise RuntimeError(
            "YouTube حظر هذا السيرفر (داتا سنتر). فعّل الفيتشر على IP نظيف "
            "(انظر ytdlp-fetcher/README.md) ثم أعد المحاولة."
        ) from e


def _fetcher_resolve(url: str) -> dict | None:
    """Resolve video metadata through the residential-IP fetcher.

    The fetcher extracts on a clean IP where YouTube is not bot-checked, so the
    container never has to hit the player API for a direct URL. Returns a dict
    (with title/duration) or None on failure.
    """
    if not _fetcher_alive():
        return None
    try:
        r = requests.get(f"{_FETCHER_URL}/resolve", params={"url": url}, timeout=60)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            LOGGER.warning(f"yt_search: fetcher resolve not-ok: {data}")
            return None
        return data
    except Exception as e:
        global _fetcher_dead_until
        _fetcher_dead_until = time.time() + 300
        LOGGER.error(f"yt_search: fetcher resolve failed ({e!r}); re-trying fetcher in 5 min")
        return None


def _build_result(e: dict) -> dict | None:
    """Normalize one yt-dlp entry into the shared result shape."""
    if not e or not e.get("id"):
        return None
    vid = e.get("id")
    dur = int(e.get("duration") or 0)
    thumbs = [t.get("url") for t in (e.get("thumbnails") or []) if isinstance(t, dict) and t.get("url")]
    if not thumbs:
        thumbs = [_thumb(vid)]
    return {
        "id": vid,
        "title": e.get("title") or "",
        "duration": f"{dur // 60}:{dur % 60:02d}",
        "url_suffix": "/watch?v=" + vid,
        "views": str(e.get("view_count") or ""),
        "channel": e.get("channel") or e.get("uploader") or "",
        "thumbnails": thumbs,
    }


def _run_coro(coro):
    """Run a coroutine from a sync call, even when called inside the running
    event loop (pyrogram handlers call yt_search synchronously)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _search_via_videos_search(query: str, max_results: int):
    """Fallback: scrape YouTube search via youtube-search-python (already a
    dependency, used by the inline module). Plain web scrape, so it bypasses
    the bot-checked innertube player API that yt-dlp's web client hits."""
    try:
        from youtubesearchpython.__future__ import VideosSearch

        async def _do():
            a = VideosSearch(query, limit=max_results)
            return (await a.next()) or {}

        res = (_run_coro(_do()).get("result")) or []
        out = []
        for x in res:
            if not x or not x.get("link"):
                continue
            m = _VID_RE.search(x.get("link") or "")
            vid = m.group(1) if m else None
            if not vid:
                continue
            thumbs = x.get("thumbnails") or []
            thumbs = [t.get("url") for t in thumbs if isinstance(t, dict) and t.get("url")] or [_thumb(vid)]
            out.append({
                "id": vid,
                "title": (x.get("title") or "").title(),
                "duration": x.get("duration") or "0:00",
                "url_suffix": "/watch?v=" + vid,
                "views": (x.get("viewCount") or {}).get("short", "") or "",
                "channel": (x.get("channel") or {}).get("name", "") or "",
                "thumbnails": thumbs,
            })
        return out
    except Exception as e:
        LOGGER.error(f"yt_search: VideosSearch fallback failed ({e!r})")
        return []


def yt_search(query: str, max_results: int = 1):
    """Search YouTube, cookie-less.

    - A direct video URL is resolved through the fetcher when configured, so
      the container never calls the bot-checked player API for the URL case.
    - A text query is searched with yt-dlp using extract_flat=True: this only
      reads the search page (one API call) instead of fully extracting every
      result, which is what triggered the "Sign in to confirm you're not a
      bot" flood on the datacenter IP. If that still fails, falls back to the
      youtube-search-python web scrape.

    Returns a list of dicts: id, title, duration ("M:SS"), url_suffix, views,
    channel, thumbnails.
    """
    opts = dict(ydl_opts)
    opts.pop("postprocessors", None)
    opts["skip_download"] = True
    # Flat search: read ONLY the search page (one request) instead of fully
    # extracting every result — full extraction is what hits the bot-checked
    # player API on the datacenter IP ("Sign in to confirm you're not a bot").
    opts["extract_flat"] = True
    q = (query or "").strip()
    if not q:
        return []

    # Direct URL → fetcher first, then full local extraction.
    if q.startswith(("http://", "https://")):
        meta = _fetcher_resolve(q)
        if meta:
            vid = _video_id(q)
            dur = int(meta.get("duration") or 0)
            LOGGER.info(f"yt_search: URL metadata via fetcher ({vid})")
            return [{
                "id": vid,
                "title": meta.get("title") or "",
                "duration": f"{dur // 60}:{dur % 60:02d}",
                "url_suffix": "/watch?v=" + vid,
                "views": "",
                "channel": "",
                "thumbnails": [_thumb(vid)],
            }]
        LOGGER.warning("yt_search: fetcher resolve failed; falling back to container extract_info")
        try:
            with YoutubeDL(opts) as ydl2:
                info = ydl2.extract_info(q, download=False)
            out = []
            entries = [info] if "entries" not in info else (info.get("entries") or [])
            for e in entries:
                r = _build_result(e)
                if r:
                    out.append(r)
            return out
        except Exception as e:
            LOGGER.error(f"yt_search: URL extract failed ({e!r})")
            return []

    # Text query → flat search (fast, one API call), then scrape fallback.
    try:
        with YoutubeDL(opts) as ydl2:
            info = ydl2.extract_info(f"ytsearch{max_results}:{q}", download=False)
        out = []
        for e in (info.get("entries") or []):
            r = _build_result(e)
            if r:
                out.append(r)
        if out:
            return out
    except Exception as e:
        LOGGER.error(f"yt_search: yt-dlp flat search failed ({e!r})")

    return _search_via_videos_search(q, max_results)
