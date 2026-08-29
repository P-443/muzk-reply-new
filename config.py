from os import getenv

from dotenv import load_dotenv

load_dotenv()


API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")

BOT_TOKEN = getenv("BOT_TOKEN", None)
DURATION_LIMIT = int(getenv("DURATION_LIMIT", "90"))

OWNER_ID = int(getenv("OWNER_ID"))

_DEFAULT_IMG = "https://cdn4.telesco.pe/file/JHOKRszNSJK6ucc7QS-8kpvfD1fl62_DmB9QyPjP4s5IWxgUI_rCk6C5XXjyQSiKlsMy94O89H0xNR9-wN0PgpMDWdKDEcK0wWSG3_lkh-6x73_yMSNucwBXU6rivUsNWyanXjz4kOzsc9nxXKzMbSJIxv4Rjwbq78l6gMQBZ9HEPkoDT48BmlKFqBYE1tVXST5IPc3CAMNxcB5e6F3ejwdQdK1vu8vH6_Y3waLCPrHKvitwXC0JRdA1LWbrd6irk1OKIsA4XqpFLtZraEdpa9ZKDhsNxWK9r9rCJuaXkZmSJmOR10sMNYetkv_mvi4WVCp8_tVk-A0pEhkGXN_g0w"
PING_IMG = getenv("PING_IMG", _DEFAULT_IMG)
START_IMG = getenv("START_IMG", _DEFAULT_IMG)

SESSION = getenv("SESSION", None)

SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/b1o_d_a")
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/b1o_d_a")

SUDO_USERS = list(map(int, getenv("SUDO_USERS", "6264668799").split()))


FAILED = _DEFAULT_IMG
