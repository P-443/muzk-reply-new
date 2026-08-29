# ShahmMusic/Helpers/captions.py
"""Play-card caption helpers.

The "Started Streaming" header line carries a Telegram CUSTOM EMOJI (by
document id) so it renders as the owner's chosen emoji in every chat.

Why this module exists: Pyrogram 2.0.97 has the raw
``MessageEntityCustomEmoji`` type but no high-level counterpart, and
``send_photo`` accepts *either* ``parse_mode`` *or* ``caption_entities``, not
both. So we parse the markdown caption ourselves, append the custom-emoji
entity at the header position, convert every raw entity back to high-level
``MessageEntity`` (which ``reply_photo``/``send_photo`` re-serialize), and hand
the pair to the caller.
"""
from pyrogram import enums
from pyrogram.enums import MessageEntityType
from pyrogram.parser import Parser
from pyrogram.raw.types import MessageEntityCustomEmoji
from pyrogram.types import MessageEntity

# The owner's custom emoji for the "Started Streaming" line (Telegram custom
# emoji document id).
STARTED_EMOJI_ID = 5974084352349311208

# Single character the custom-emoji entity covers at offset 0. Telegram
# replaces it with the actual emoji, so it is never visible; it only has to be
# a real char so the entity range is valid.
_PH = "▶"

# Reverse map: raw entity class -> high-level MessageEntityType, used to
# convert the markdown-parsed raw entities back to high-level entities.
_REV = {e.value: e for e in MessageEntityType}


def _to_high_level(raw):
    """Map a raw entity to a high-level MessageEntity (None if unmapped)."""
    t = _REV.get(type(raw))
    if t is None:
        return None
    return MessageEntity(
        type=t,
        offset=raw.offset,
        length=raw.length,
        url=getattr(raw, "url", None),
        custom_emoji_id=getattr(raw, "document_id", None),
    )


async def caption_with_started_emoji(caption: str, client=None):
    """Replace the header's ``⌔︙`` with the custom emoji.

    ``caption`` is the usual markdown caption starting with
    ``**⌔︙ Sᴛᴀʀᴛᴇᴅ Sᴛʀᴇᴀᴍɪɴɢ |**``. Returns ``(text, caption_entities)`` to
    pass to ``reply_photo(..., caption=text, caption_entities=caption_entities)``.
    """
    # Swap the decorative ⌔︙ on the Started Streaming header line for the emoji
    # placeholder (only the first occurrence -- the Tɪᴛʟᴇ/Dᴜʀᴀᴛɪᴏɴ/Rᴇǫᴜᴇsᴛᴇᴅ
    # lines keep their own ⌔︙).
    caption = caption.replace("⌔︙ Sᴛᴀʀᴛᴇᴅ", _PH + " Sᴛᴀʀᴛᴇᴅ", 1)
    parsed = await Parser(client).parse(caption, enums.ParseMode.DEFAULT)
    text = parsed["message"]
    raw_entities = list(parsed["entities"])
    raw_entities.append(
        MessageEntityCustomEmoji(offset=0, length=1, document_id=STARTED_EMOJI_ID)
    )
    raw_entities.sort(key=lambda e: e.offset)
    caption_entities = [
        hl for raw in raw_entities if (hl := _to_high_level(raw)) is not None
    ]
    return text, caption_entities
