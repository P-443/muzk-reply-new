"""Decisive test: can a bgutil-minted PO token bypass the bot-check on this IP?"""
import base64, json, re, subprocess, sys, urllib.request

VID = "rPhbE6Tc8zo"
def log(*a):
    print(*a, flush=True)

# 1. fetch watch page
try:
    html = urllib.request.urlopen(
        f"https://www.youtube.com/watch?v={VID}", timeout=20
    ).read().decode("utf-8", "replace")
    log("webpage bytes:", len(html))
except Exception as e:
    log("webpage fetch FAILED:", repr(e)); sys.exit(2)

# 2. extract attestation — mirror the plugin's _get_attestation exactly
from yt_dlp.utils import js_to_json
ch = None

# 2a. window.ytAtN({...});
m = re.search(r"""(?sx)window\s*\.\s*ytAtN\s*\(\s*
                    (?P<js>\{.+?\}\s*)
                \s*\)\s*;""", html)
if m:
    try:
        obj = json.loads(js_to_json(m.group("js")))
        if isinstance(obj, dict) and isinstance(obj.get("R"), str):
            obj = json.loads(obj["R"])
        if isinstance(obj, dict):
            ch = obj.get("bgChallenge")
    except Exception as e:
        log("ytAtN parse:", repr(e)[:80])
log("attestation via ytAtN:", bool(ch))

# 2b. window.ytAtR = "...";
if not ch:
    m = re.search(r"""(?sx)window\.ytAtR\s*=\s*(?P<raw_cd>(?P<q>['"])
                        (?:\\.|(?!(?P=q)).)*
                    (?P=q))\s*;""", html)
    if m:
        try:
            raw = m.group("raw_cd")
            obj = json.loads(js_to_json(raw))
            if isinstance(obj, dict):
                ch = obj.get("bgChallenge")
        except Exception as e:
            log("ytAtR parse:", repr(e)[:80])
log("attestation via ytAtR:", bool(ch))
if not ch:
    log("NO attestation found -> cannot mint (matches hard IP block with no challenge)")
    sys.exit(2)

# 3. content_binding = video_id (PLAYER context, per get_webpo_content_binding)
mv = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION"\s*:\s*"([^"]+)"', html)
ver = mv.group(1) if mv else "2.20250801.00.00"
log("client version:", ver)
payload = {
    "bypass_cache": False,
    "challenge": ch,
    "content_binding": VID,
    "disable_tls_verification": False,
    "proxy": None,
    "innertube_context": {"client": {"clientName": "WEB", "clientVersion": ver}},
    "source_address": None,
}
req = urllib.request.Request(
    "http://127.0.0.1:4416/get_pot",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    resp = json.load(urllib.request.urlopen(req, timeout=25))
except Exception as e:
    log("get_pot FAILED:", repr(e)); sys.exit(2)
tok = resp.get("poToken")
log("minted token:", bool(tok), (tok[:24] + "..." if tok else resp))
if not tok:
    sys.exit(2)

# 4. run yt-dlp web client WITH the token
cmd = [
    "python3", "-m", "yt_dlp", "--skip-download", "--no-warnings",
    "--extractor-args", f"youtube:player_client=web;po_token=web+{tok}",
    "--print", "%(title)s",
    f"https://www.youtube.com/watch?v={VID}",
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
log("---")
log("EXIT:", r.returncode)
log("OUT:", (r.stdout or "")[-300:].strip())
log("ERR:", (r.stderr or "")[-600:].strip())
