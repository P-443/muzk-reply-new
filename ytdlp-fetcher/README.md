# Residential fetcher for the muzk bot

The Coolify server IP (`147.93.55.93`) is hard bot-checked by YouTube. We
proved that even valid, attested bgutil PO tokens do NOT bypass it — the block
is at the IP-reputation level. The container can therefore only download
through a **clean egress IP**, which is what this little service provides.

## Run it (on your home PC / any clean IP)

```bash
pip install yt-dlp flask
python fetcher.py            # listens on 0.0.0.0:8080
```

Requires `ffmpeg` on PATH (for the mp3 conversion).

## Expose it durably

`cloudflared tunnel --url http://localhost:8080` gives a URL but dies with the
terminal. For a **stable** URL use a named tunnel with your `ar-senik.pro`
domain, or keep the process running as a service (nssm / Task Scheduler /
screen). Example quick start:

```bash
cloudflared tunnel --url http://localhost:8080
```

Copy the `https://...trycloudflare.com` URL that prints.

## Tell the bot about it

In Coolify → app **muzk-reply-new** → Environment Variables, set:

```
YTDLP_FETCHER_URL=https://<your-tunnel-url>
```

(no trailing slash). The bot tries the fetcher first, and only falls back to
its own yt-dlp (which works on clean IPs but not this one).

## Endpoints

| Route | Purpose |
|---|---|
| `GET /ping` | health check |
| `GET /resolve?url=...` | video metadata (title/duration) |
| `GET /get_audio?url=...` | streams the mp3 back (192k), deletes after |
