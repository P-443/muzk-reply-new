from os import getenv

from dotenv import load_dotenv

load_dotenv()


API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")

BOT_TOKEN = getenv("BOT_TOKEN", None)
DURATION_LIMIT = int(getenv("DURATION_LIMIT", "90"))

OWNER_ID = int(getenv("OWNER_ID"))

_DEFAULT_IMG = "https://files.catbox.moe/ldyndf.jpg"
PING_IMG = getenv("PING_IMG", _DEFAULT_IMG)
START_IMG = getenv("START_IMG", _DEFAULT_IMG)

SESSION = getenv("SESSION", None)

SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/b1o_d_a")
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/b1o_d_a")

SUDO_USERS = list(map(int, getenv("SUDO_USERS", "6264668799").split()))


FAILED = _DEFAULT_IMG
