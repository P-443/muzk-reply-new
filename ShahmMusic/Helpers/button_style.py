
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

# The 🎧 custom emoji the owner asked to put on every button.
HEADPHONE_EMOJI_ID = "6007938409857815902"

_TOKEN = config.BOT_TOKEN
_BASE = (config.BOT_API_URL if hasattr(config, "BOT_API_URL") else None) or "https://api.telegram.org"
_BASE = _BASE.rstrip("/")
_API = f"{_BASE}/bot{_TOKEN}/editMessageReplyMarkup" if _TOKEN else None


def _style_for(btn: InlineKeyboardButton) -> tuple:
    """Pick (style, icon) for a button by its callback_data.

    Primary = blue, success = green, danger = red, secondary = grey.
    """
    cd = str(btn.callback_data or "")
    if cd == "close" or cd == "end_cb" or cd.startswith("forceclose"):
        return "danger", HEADPHONE_EMOJI_ID
    if cd.startswith("unban_assistant"):
        return "success", HEADPHONE_EMOJI_ID
    # everything else (resume/pause/skip, help menu, url links, user buttons)
    return "primary", HEADPHONE_EMOJI_ID


def _to_api_button(btn: InlineKeyboardButton) -> dict:
    out = {"text": btn.text or ""}
    if btn.url is not None:
        out["url"] = btn.url
    elif getattr(btn, "user_id", None) is not None:
        out["user_id"] = int(btn.user_id)
    elif btn.callback_data is not None:
        out["callback_data"] = str(btn.callback_data)
    # switch_inline_query / web_app / login_url aren't used by this bot.

    # Color + custom emoji icon on every labeled button. Empty spacer buttons
    # (the invisible support/developer placeholders) stay bare.
    if btn.text:
        style, icon = _style_for(btn)
        out["style"] = style
        out["icon_custom_emoji_id"] = icon
    return out


def to_botapi_keyboard(markup: InlineKeyboardMarkup) -> dict:
    return {
        "inline_keyboard": [
            [_to_api_button(b) for b in row] for row in markup.inline_keyboard
        ]
    }


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
