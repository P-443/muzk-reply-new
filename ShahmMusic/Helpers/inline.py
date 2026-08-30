
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from ShahmMusic import BOT_USERNAME
from ShahmMusic.Helpers.button_style import CLOSE_TEXT


def _close_button(callback="close"):
    """Close button showing the 3 close emojis (⬅️🚫➡️) as text.

    Telegram only allows one custom emoji per button, so the close emojis are
    the plain ⬅️🚫➡️ characters. apply_styles still colors it danger/red.
    """
    return InlineKeyboardButton(text=CLOSE_TEXT, callback_data=callback)


close_key = InlineKeyboardMarkup(
    [[_close_button()]]
)


buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="▷", callback_data="resume_cb"),
    ],
    [
            InlineKeyboardButton(text=" II ", callback_data="pause_cb"),
            InlineKeyboardButton(text="‣‣I", callback_data="skip_cb"),
            InlineKeyboardButton(text="▢", callback_data="end_cb"),
        ]
    ]
)


pm_buttons = [
    [
        InlineKeyboardButton(
            text="اضفني لمجموعتك",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        )
    ],
    [InlineKeyboardButton(text="الاوامر", callback_data="Shahm_help")],
    [
        InlineKeyboardButton(text="", url=config.SUPPORT_CHANNEL),
        InlineKeyboardButton(text="", url=config.SUPPORT_CHAT),
    ],
    [
        InlineKeyboardButton(
            text="", url="https://t.me/KOK0KK"
        ),
        InlineKeyboardButton(text="مالك البوت", user_id=config.OWNER_ID),
    ],
]


gp_buttons = [
    [
        InlineKeyboardButton(
            text="اضفني لمجموعتك",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        )
    ],
    [
        InlineKeyboardButton(text="السورس", url=config.SUPPORT_CHANNEL),
        InlineKeyboardButton(text="التحديثات", url=config.SUPPORT_CHAT),
    ],
    [
        InlineKeyboardButton(
            text="المطور", url="https://t.me/KOK0KK"
        ),
        InlineKeyboardButton(text="مالك البوت", user_id=config.OWNER_ID),
    ],
]


helpmenu = [
    [
        InlineKeyboardButton(
            text="الاوامر",
            callback_data="Shahm_cb help",
        )
    ],
    [
        InlineKeyboardButton(text="اوامࢪ المطور", callback_data="Shahm_cb sudo"),
        InlineKeyboardButton(text="اوامر المالك", callback_data="Shahm_cb owner"),
    ],
    [
        InlineKeyboardButton(text="عودة", callback_data="Shahm_home"),
        _close_button(),
    ],
]


help_back = [
    [InlineKeyboardButton(text="السورس", url=config.SUPPORT_CHAT)],
    [
        InlineKeyboardButton(text="عودة", callback_data="Shahm_help"),
        _close_button(),
    ],
]
