#!/usr/bin/env python3
"""Residential-IP fetcher for the muzk bot.

The Coolify server's IP is hard bot-checked by YouTube ("Sign in to confirm
you're not a bot"). No cookie-less trick (PO tokens, OAuth, player clients)
bypasses that -- it's an IP-reputation gate. So the container asks THIS small
service -- running on a residential/clean IP where YouTube is NOT blocked -- to
resolve + download + convert the audio, and it streams the mp3 back.

Run it on a machine with a clean IP (e.g. your home PC), Python 3.9+, and
yt-dlp + ffmpeg installed:

    pip install yt-dlp flask          # one time
    python fetcher.py                  # listens on 0.0.0.0:8080

Expose it with a tunnel that STAYS UP. A plain `cloudflared tunnel --url`
process dies with the terminal -- prefer a named tunnel (stable URL) or keep
the process running (screen/nssm/Windows task). Example temporary:

    cloudflared tunnel --url http://localhost:8080

Then set the bot's env var in Coolify (no trailing slash):

    YTDLP_FETCHER_URL = https://your-tunnel-url

Endpoints used by the bot:
    GET /ping       -> {"ok": true}
    GET /resolve?url=... -> {"ok":true,"id":..,"title":..,"duration":<sec>}
    GET /get_audio?url=... -> streamed mp3 (192k), deleted after send
"""
import json
import os
import threading

from flask import Flask, Response, jsonify, request
from yt_dlp import YoutubeDL

app = Flask(__name__)

OPT = {
    "format": "bestaudio/best",
    "outtmpl": "dl/%(id)s.%(ext)s",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "retries": 5,
    "fragment_retries": 5,
    # mobile/embedded clients are not bot-checked the way "web" is on a clean IP
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "ios", "mweb", "tv", "web"],
        }
    },
    "postprocessors": [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
    ],
}
os.makedirs("dl", exist_ok=True)
_lock = threading.Lock()


@app.get("/ping")
def ping():
    return jsonify(ok=True)


@app.get("/resolve")
def resolve():
    url = request.args.get("url", "")
    try:
        with YoutubeDL({**OPT, "skip_download": True, "postprocessors": []}) as y:
            info = y.extract_info(url, download=False)
        return jsonify(
            ok=True,
            id=info.get("id") or "",
            title=info.get("title") or "",
            duration=int(info.get("duration") or 0),
        )
    except Exception as e:
        return jsonify(ok=False, error=repr(e)), 502


@app.get("/get_audio")
def get_audio():
    url = request.args.get("url", "")
    try:
        with _lock:
            with YoutubeDL(OPT) as y:
                info = y.extract_info(url, download=True)
            vid = info.get("id") or "song"
            path = os.path.join("dl", f"{vid}.mp3")
            if not os.path.exists(path):
                return jsonify(ok=False, error="audio not produced"), 502

            def stream():
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        yield chunk
                try:
                    os.remove(path)
                except Exception:
                    pass

            return Response(
                stream(),
                mimetype="audio/mpeg",
                headers={"Content-Disposition": f'attachment; filename="{vid}.mp3"'},
            )
    except Exception as e:
        return jsonify(ok=False, error=repr(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
