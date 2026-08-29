
import os

from pyrogram import filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from ShahmMusic import BOT_MENTION, BOT_NAME, app, app2
from ShahmMusic.Helpers import gp_buttons, pm_buttons
from ShahmMusic.Helpers.button_style import apply_styles
from ShahmMusic.Helpers.dossier import *


_START_VIDEO = None


async def _get_start_video() -> str | None:
    """Fetch the channel welcome video (t.me/Depr_essi_on/63) and cache it on disk.

    Public t.me pages only expose the poster, and Telegram's servers cannot
    fetch telesco.pe/CDN links. So the bot downloads the video with its own
    user session and sends it as a local file. Falls back to the static image
    when the video can't be obtained.
    """
    global _START_VIDEO
    if _START_VIDEO and os.path.exists(_START_VIDEO):
        return _START_VIDEO
    try:
        chat = await app2.get_chat("Depr_essi_on")
        msg = await app2.get_messages(chat.id, 63)
        if msg and msg.video:
            path = await app2.download_media(msg, file_name="welcome_video.mp4")
            if path and os.path.exists(path):
                _START_VIDEO = path
                return path
    except Exception:
        pass
    return None



@app.on_message(filters.command(["start"]) | filters.command(["لسورس","السورس","المطور"],prefixes= ["/", "!","","#"]) & ~filters.forwarded)
@app.on_edited_message(filters.command(["start"]) & ~filters.forwarded)
async def Shahm_st(_, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        if len(message.text.split()) > 1:
            cmd = message.text.split(None, 1)[1]
            if cmd[0:3] == "inf":
                m = await message.reply_text("** انتظر من فضلك**")
                query = (str(cmd)).replace("info_", "", 1)
                query = f"https://www.youtube.com/watch?v={query}"
                results = VideosSearch(query, limit=1)
                for result in (await results.next())["result"]:
                    title = result["title"]
                    duration = result["duration"]
                    views = result["viewCount"]["short"]
                    thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                    channellink = result["channel"]["link"]
                    channel = result["channel"]["name"]
                    link = result["link"]
                    published = result["publishedTime"]
                searched_text = f"""
⌔︙ **تتبع المعلومات ** 

⌔︙ **العنوان :** {title}

⌔︙ **المدة :** {duration} دقيقة
⌔︙ **الآراء :** `{views}`
⌔︙ **نشرت في :** {published}
⌔︙ **الرابط :** v [اضغط هنا]({link})
⌔︙ **القناة :** [{channel}]({channellink})

⌔︙ بحث بواسطة {BOT_NAME}"""
                key = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="‹ : اليوتيوب : ›", url=link),
                            InlineKeyboardButton(
                                text="‹ : التحديثات : ›", url=config.SUPPORT_CHAT
                            ),
                        ],
                    ]
                )
                await m.delete()
                inf_msg = await app.send_photo(
                    message.chat.id,
                    photo=thumbnail,
                    caption=searched_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=key,
                )
                return await apply_styles(inf_msg, key)
        else:
            pm_kb = InlineKeyboardMarkup(pm_buttons)
            caption = PM_START_TEXT.format(
                message.from_user.first_name,
                BOT_MENTION,
            )
            video = await _get_start_video()
            if video:
                pm_msg = await message.reply_video(
                    video=video,
                    caption=caption,
                    reply_markup=pm_kb,
                )
            else:
                pm_msg = await message.reply_photo(
                    photo=config.START_IMG,
                    caption=caption,
                    reply_markup=pm_kb,
                )
            await apply_styles(pm_msg, pm_kb)
    else:
        gp_kb = InlineKeyboardMarkup(gp_buttons)
        caption = START_TEXT.format(
            message.from_user.first_name,
            BOT_MENTION,
            message.chat.title,
            config.SUPPORT_CHAT,
        )
        video = await _get_start_video()
        if video:
            gp_msg = await message.reply_video(
                video=video,
                caption=caption,
                reply_markup=gp_kb,
            )
        else:
            gp_msg = await message.reply_photo(
                photo=config.START_IMG,
                caption=caption,
                reply_markup=gp_kb,
            )
        await apply_styles(gp_msg, gp_kb)
