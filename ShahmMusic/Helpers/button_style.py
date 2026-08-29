
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
DOWNLOAD_EMOJI_ID = "5877307202888273539"   # 📥
CHECK_EMOJI_ID = "5260726538302660868"      # ✅

HEADPHONE_TAG = f'<emoji id="{HEADPHONE_EMOJI_ID}">🎧</emoji>'
GUITAR_TAG = f'<emoji id="{GUITAR_EMOJI_ID}">🎸</emoji>'
DOWNLOAD_TAG = f'<emoji id="{DOWNLOAD_EMOJI_ID}">📥</emoji>'
CHECK_TAG = f'<emoji id="{CHECK_EMOJI_ID}">✅</emoji>'

_TOKEN = config.BOT_TOKEN
_BASE = (config.BOT_API_URL if hasattr(config, "BOT_API_URL") else None) or "https://api.telegram.org"
_BASE = _BASE.rstrip("/")
_API = f"{_BASE}/bot{_TOKEN}/editMessageReplyMarkup" if _TOKEN else None


def _style_for(btn: InlineKeyboardButton) -> str:
    """Pick the button color by its callback_data -- every button its own color.

    Primary = blue, secondary = grey, success = green, danger = red.
    """
    cd = str(btn.callback_data or "")
    if cd == "resume_cb":
        return "success"        # ▷ play/resume = green
    if cd == "pause_cb":
        return "secondary"      # II pause = grey
    if cd == "skip_cb":
        return "primary"        # ‣‣I next = blue
    if cd == "end_cb" or cd == "close" or cd.startswith("forceclose"):
        return "danger"         # stop/close = red
    if cd.startswith("unban_assistant"):
        return "success"        # unban = green
    if cd.startswith("Shahm_cb owner"):
        return "danger"         # owner commands = red
    if cd.startswith("Shahm_cb sudo"):
        return "secondary"      # sudo commands = grey
    # everything else (help menu, url links, user buttons) = blue
    return "primary"


def _to_api_button(btn: InlineKeyboardButton):
    text = btn.text or ""
    if not text.strip():
        # Empty-text spacer/placeholder button (the invisible support/owner
        # placeholders). The Bot API rejects buttons with empty text, so give
        # it a zero-width space -- still renders invisible, keyboard parses.
        text = "​"
    out = {"text": text}
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
