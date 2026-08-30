
"""Styled inline buttons (colored + custom emoji icons) via the HTTP Bot API.

Pyrogram (MTProto) cannot render colored inline buttons or button icons --
those are HTTP Bot API 7.0+ features and the color only shows for Telegram
Premium users. So the bot always sends its normal keyboard first (so the
buttons always work, even if the HTTP restyle fails), then this module
replaces that keyboard over the Bot API with a styled copy that carries
`style` and `icon_custom_emoji_id` on every labeled button.

Requires BOT_TOKEN (already set in the app env) and a Premium account
actually viewing the buttons to see the colors.
"""

import config
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ShahmMusic import LOGGER

# Premium custom emojis the owner provided, for use inside message texts.
# Pyrogram renders <emoji id="..."> as the real premium emoji (MessageEntityCustomEmoji).
HEADPHONE_EMOJI_ID = "6007938409857815902"  # 🎧
GUITAR_EMOJI_ID = "5348242647351834121"     # 🎸
DOWNLOAD_EMOJI_ID = "5444961234933806330"   # ⬇️
CHECK_EMOJI_ID = "5260726538302660868"      # ✅
THUNDER_EMOJI_ID = "5219943216781995020"    # ⚡
SMILE_EMOJI_ID = "5222108309795908493"      # 😊
STARTED_EMOJI_ID = "5974084352349311208"    # the owner's emoji for the Started Streaming line

# The owner's 3 premium emojis for the "اغلاق" (close) buttons are premium
# versions of ⬅️ 🚫 ➡️. Telegram allows only ONE custom emoji per button
# (icon_custom_emoji_id) and does not render <emoji id> inside button text, so
# the close button shows the first emoji as the premium icon (it renders in
# its own icon slot on the left) and the other two as plain text:
# premium ⬅️ + 🚫 + ➡️, in one button, with no placeholder text.
CLOSE_EMOJI_IDS = (
    "5447389832781264371",  # premium ⬅️ (used as the button icon)
    "5447647474984449520",  # premium 🚫
    "5447181973544008180",  # premium ➡️
)
CLOSE_TEXT = "🚫➡️"  # the text after the premium ⬅️ icon (no duplicate, no ▪)

HEADPHONE_TAG = f'<emoji id="{HEADPHONE_EMOJI_ID}">🎧</emoji>'
GUITAR_TAG = f'<emoji id="{GUITAR_EMOJI_ID}">🎸</emoji>'
DOWNLOAD_TAG = f'<emoji id="{DOWNLOAD_EMOJI_ID}">⬇️</emoji>'
CHECK_TAG = f'<emoji id="{CHECK_EMOJI_ID}">✅</emoji>'
THUNDER_TAG = f'<emoji id="{THUNDER_EMOJI_ID}">⚡</emoji>'
SMILE_TAG = f'<emoji id="{SMILE_EMOJI_ID}">😊</emoji>'
STARTED_TAG = f'<emoji id="{STARTED_EMOJI_ID}">🎵</emoji>'

_TOKEN = config.BOT_TOKEN
_BASE = (config.BOT_API_URL if hasattr(config, "BOT_API_URL") else None) or "https://api.telegram.org"
_BASE = _BASE.rstrip("/")
_API = f"{_BASE}/bot{_TOKEN}/editMessageReplyMarkup" if _TOKEN else None


def _style_for(btn: InlineKeyboardButton) -> str:
    """Pick the button color by its callback_data -- every button its own color.

    Valid Bot API style values are `primary`, `default`, `success` and `danger`
    (verified live against the API -- `secondary` is rejected with "Invalid
    button style specified"). Primary = blue, default = grey, success = green,
    danger = red.
    """
    cd = str(btn.callback_data or "")
    if cd == "resume_cb":
        return "success"        # ▷ play/resume = green
    if cd == "pause_cb":
        return "default"        # II pause = grey
    if cd == "skip_cb":
        return "primary"        # ‣‣I next = blue
    if cd == "end_cb" or cd == "close" or cd.startswith("forceclose"):
        return "danger"         # stop/close = red
    if cd.startswith("unban_assistant"):
        return "success"        # unban = green
    if cd.startswith("Shahm_cb owner"):
        return "danger"         # owner commands = red
    if cd.startswith("Shahm_cb sudo"):
        return "default"        # sudo commands = grey
    # everything else (help menu, url links, user buttons) = blue
    return "primary"


def _to_api_button(btn: InlineKeyboardButton):
    text = btn.text or ""
    icon = getattr(btn, "_icon_id", None)
    if not text.strip() and not icon:
        # Empty-text spacer/placeholder button (the invisible support/owner
        # placeholders). Drop it entirely -- a zero-width-space stand-in
        # renders as stray invisible buttons in some clients.
        return None
    out = {"text": text}
    if icon:
        # Custom emoji icon on the button (Bot API 7.0+). The icon renders
        # instead of the first char of the text, so the "▪" placeholder text
        # disappears and the button is just the owner's premium emoji.
        out["icon_custom_emoji_id"] = icon
    if btn.url:
        out["url"] = btn.url
    elif getattr(btn, "user_id", None) is not None:
        # The Bot API has no `user_id` button type -- Telegram's parser sees a
        # button with only text and rejects it. Reproduce it as a tg://user
        # deep link, which opens the same user's chat.
        out["url"] = f"tg://user?id={int(btn.user_id)}"
    elif btn.callback_data is not None:
        out["callback_data"] = str(btn.callback_data)
    else:
        # Text-only (or empty spacer with no action) -- Telegram rejects
        # those, so drop the button instead.
        return None
    # switch_inline_query / web_app / login_url aren't used by this bot.

    # Color on every labeled button. Empty spacer buttons stay plain.
    if text.strip():
        out["style"] = _style_for(btn)
    return out


def to_botapi_keyboard(markup: InlineKeyboardMarkup) -> dict:
    rows = []
    for row in markup.inline_keyboard:
        parsed = [b for b in (_to_api_button(x) for x in row) if b is not None]
        if parsed:
            rows.append(parsed)
    return {"inline_keyboard": rows}


async def apply_styles(message: Message, markup=None) -> None:
    """Restyle an already-sent/edited message's keyboard over the Bot API.

    `message` is the pyrogram Message (its chat.id + id address the message to
    the Bot API). `markup` defaults to message.reply_markup. Failures are
    logged and swallowed so the bot keeps working with the plain keyboard.
    """
    if _API is None:
        return  # no BOT_TOKEN -> nothing to restyle
    if markup is None:
        markup = message.reply_markup
    if not markup or not markup.inline_keyboard:
        return
    payload = {
        "chat_id": message.chat.id,
        "message_id": message.id,
        "reply_markup": to_botapi_keyboard(markup),
    }
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                _API, json=payload, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                body = await resp.text()
                if resp.status != 200:
                    LOGGER.warning(
                        "button_style: restyle failed (%s): %s", resp.status, body[:200]
                    )
    except Exception as e:
        LOGGER.warning("button_style: restyle error: %r", e)
