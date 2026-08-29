import asyncio
import os
import re
import threading

import requests
from yt_dlp import YoutubeDL

from ShahmMusic import LOGGER

# Cookie-less by default. On a datacenter IP, YouTube rejects cookies, login
# and PO tokens with "Sign in to confirm you're not a bot" -- the ONLY working
# fix is clean egress via YTDLP_PROXY. On this Coolify server that is the
# deployed Cloudflare WARP proxy (socks5h://10.0.1.1:9091, set at the app
# level), which routes yt-dlp through Cloudflare so the player API is not
# bot-checked. A residential proxy also works: YTDLP_PROXY=https://user:pass@host:port.
#
# YTDLP_FETCHER_URL: when set, audio_dl downloads through a small "fetcher"
# service running on a residential-IP machine (ytdlp-fetcher/fetcher.py).
# That service resolves + converts the video with yt-dlp from a clean IP and
# streams the mp3 back, sidestepping the datacenter-IP bot-check entirely.
_FETCHER_URL = os.getenv("YTDLP_FETCHER_URL")
_COOKIES = os.getenv("YTDLP_COOKIES")
_PROXY = os.getenv("YTDLP_PROXY")


def _redact(v: str) -> str:
    """Redact a secret for the logs (proxy creds etc.)."""
    if not v:
        return "NOT SET"
    if len(v) <= 12:
        return v[:3] + "***"
    return v[:6] + "..." + v[-3:]


def _cookie_stats(path):
    """Return (size_bytes, entry_count) for a cookies file, or None if absent.

    Strong boot logging so Coolify shows exactly which cookies file yt-dlp
    will use and whether it parsed any entries.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        entries = sum(1 for ln in lines if ln and not ln.startswith("#"))
        return (os.path.getsize(path), entries)
    except Exception as e:
        LOGGER.warning(f"downloaders: cannot read cookies file {path!r}: {e!r}")
        return None


_COOKIE_STAT = _cookie_stats(_COOKIES)
if _COOKIE_STAT:
    LOGGER.info(
        "downloaders: cookiefile=%s size=%dB entries=%d",
        _COOKIES, _COOKIE_STAT[0], _COOKIE_STAT[1],
    )
LOGGER.info(
    "downloaders: YTDLP_FETCHER_URL=%s YTDLP_COOKIES=%s YTDLP_PROXY=%s",
    "SET" if _FETCHER_URL else "NOT SET",
    "SET" if _COOKIES else "NOT SET",
    "SET" if _PROXY else "NOT SET",
)

_VID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")


def run_in_thread(func, *args):
    """Run a blocking function in a daemon thread, returning an awaitable.

    yt-dlp / requests downloads are synchronous and would otherwise block the
    whole asyncio event loop, freezing the bot (no replies, no restart) for the
    entire download. Offloading to a thread keeps the bot responsive. The
    thread is daemon so a process restart mid-download does NOT wait for the
    download to finish -- the container exits immediately.
    """
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def _run():
        try:
            result = func(*args)
            loop.call_soon_threadsafe(fut.set_result, result)
        except BaseException as e:  # noqa: BLE001 - deliver any error to the caller
            loop.call_soon_threadsafe(fut.set_exception, e)

    threading.Thread(target=_run, daemon=True).start()
    return fut


def _video_id(url: str) -> str:
    m = _VID_RE.search(url or "")
    return m.group(1) if m else "song"

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
            # 192 kbps: re-encoding to 320 was a big CPU + download cost on the
            # proxied server and delayed playback start a lot. 192 still sounds
            # clean in a Telegram voice call but encodes roughly 2x faster.
            "preferredquality": "192",
        }
    ],
}

if _COOKIE_STAT:
    ydl_opts["cookiefile"] = _COOKIES
    LOGGER.info("downloaders: cookiefile wired -> %s", _COOKIES)
elif _COOKIES:
    LOGGER.warning("downloaders: YTDLP_COOKIES set but file missing/empty: %s", _COOKIES)
if _PROXY:
    ydl_opts["proxy"] = _PROXY

LOGGER.info(
    "downloaders: yt-dlp player_clients=%s",
    ydl_opts["extractor_args"]["youtube"]["player_client"],
)
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
    vid = _video_id(url)
    if _FETCHER_URL:
        try:
            LOGGER.info(f"audio_dl: [{vid}] fetching via fetcher ({_FETCHER_URL})")
            return _audio_dl_via_fetcher(url)
        except Exception as e:
            LOGGER.error(f"audio_dl: [{vid}] fetcher failed ({e!r}); falling back to yt-dlp")
    LOGGER.info(
        "audio_dl: [%s] container yt-dlp cookiefile=%s proxy=%s",
        vid,
        os.path.basename(_COOKIES) if _COOKIE_STAT else "none",
        _redact(_PROXY),
    )
    try:
        sin = ydl.extract_info(url, False)
    except Exception as e:
        LOGGER.error("audio_dl: [%s] extract_info FAILED: %r", vid, e)
        if "Sign in to confirm" in str(e) or "not a bot" in str(e):
            LOGGER.error(
                "audio_dl: [%s] DIAGNOSIS: this container's datacenter IP is "
                "flagged by YouTube -- cookies/login/PO tokens do NOT bypass "
                "it. Working fix: YTDLP_PROXY=<socks5 proxy with clean egress> "
                "(on this server: the deployed WARP proxy "
                "socks5h://10.0.1.1:9091).",
                vid,
            )
        raise
    x_file = os.path.join("downloads", f"{sin['id']}.mp3")
    if os.path.exists(x_file):
        return x_file
    LOGGER.info("audio_dl: [%s] downloading audio stream...", vid)
    ydl.download([url])
    LOGGER.info("audio_dl: [%s] done -> %s", vid, x_file)
    return x_file


def _fetcher_resolve(url: str) -> dict | None:
    """Resolve video metadata through the residential-IP fetcher.

    The fetcher extracts on a clean IP where YouTube is not bot-checked, so the
    container never has to hit the player API for a direct URL. Returns a dict
    (with title/duration) or None on failure.
    """
    if not _FETCHER_URL:
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
        LOGGER.error(f"yt_search: fetcher resolve failed ({e!r})")
        return None


def yt_search(query: str, max_results: int = 1):
    """Search YouTube via yt-dlp (reuses the same cookies/client config).

    Returns a list of dicts shaped like the legacy youtube_search lib:
    id, title, duration ("M:SS"), url_suffix, views, channel, thumbnails.

    A direct video URL is resolved through the fetcher when configured, so the
    container never calls the bot-checked player API for the URL case.
    """
    opts = dict(ydl_opts)
    opts.pop("postprocessors", None)
    opts["skip_download"] = True
    # Flat search: read ONLY the search page (one request) instead of fully
    # extracting every result -- full extraction is what hits the bot-checked
    # player API on the datacenter IP ("Sign in to confirm you're not a bot").
    opts["extract_flat"] = True
    q = (query or "").strip()
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
                "thumbnails": [f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"],
            }]
        LOGGER.warning("yt_search: fetcher resolve failed; cannot resolve URL from this IP")
        target = q
    else:
        target = f"ytsearch{max_results}:{q}"
    try:
        with YoutubeDL(opts) as search_ydl:
            info = search_ydl.extract_info(target, download=False)
    except Exception as e:
        LOGGER.error("yt_search: extract_info FAILED for %r: %r", q, e)
        if "Sign in to confirm" in str(e) or "not a bot" in str(e):
            LOGGER.error(
                "yt_search: DIAGNOSIS: this container's datacenter IP is flagged "
                "by YouTube -- cookies/login/PO tokens do NOT bypass it. Working "
                "fix: YTDLP_PROXY=<socks5 proxy with clean egress> (on this "
                "server: the deployed WARP proxy socks5h://10.0.1.1:9091).",
            )
        raise
    entries = [info] if "entries" not in info else (info.get("entries") or [])
    out = []
    for e in entries:
        if not e or not e.get("id"):
            continue
        vid = e.get("id")
        dur = int(e.get("duration") or 0)
        thumbs = [
            t.get("url") for t in (e.get("thumbnails") or [])
            if isinstance(t, dict) and t.get("url")
        ]
        if not thumbs:
            thumbs = [f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"]
        out.append({
            "id": vid,
            "title": e.get("title") or "",
            "duration": f"{dur // 60}:{dur % 60:02d}",
            "url_suffix": "/watch?v=" + vid,
            "views": str(e.get("view_count") or ""),
            "channel": e.get("channel") or e.get("uploader") or "",
            "thumbnails": thumbs,
        })
    LOGGER.info("yt_search: %r -> %d result(s)", q, len(out))
    return out