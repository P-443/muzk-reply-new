
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from ShahmMusic import BOT_USERNAME
from ShahmMusic.Helpers.button_style import CLOSE_EMOJI_IDS, CLOSE_TEXT


def _close_button(callback="close"):
    """Close button with premium 🚫 icon + ➡️ text.

    Uses the second premium emoji as icon and the third as text, resulting
    in a single button showing 🚫 (premium) + ➡️ (plain).
    """
    b = InlineKeyboardButton(text=CLOSE_TEXT, callback_data=callback)
    b._icon_id = CLOSE_EMOJI_IDS[0]
    return b


def _close_button_icon_only(callback="close"):
    """Close button showing only the premium 🚫 icon, no visible text.

    Uses zero-width space as text so only the premium emoji renders.
    """
    b = InlineKeyboardButton(text="‌", callback_data=callback)
    b._icon_id = CLOSE_EMOJI_IDS[0]
    return b


def _back_button(callback):
    """Return button with premium ⬅️ icon + 'عودة' text.

    Uses the back arrow premium emoji as icon alongside the word 'عودة'.
    """
    b = InlineKeyboardButton(text="عودة", callback_data=callback)
    b._icon_id = CLOSE_EMOJI_IDS[1]  # ⬅️
    return b


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
        _back_button("Shahm_home"),
        _close_button_icon_only(),
    ],
]


help_back = [
    [InlineKeyboardButton(text="السورس", url=config.SUPPORT_CHAT)],
    [
        _back_button("Shahm_help"),
        _close_button_icon_only(),
    ],
]
