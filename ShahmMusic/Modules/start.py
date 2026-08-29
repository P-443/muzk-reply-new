
from pyrogram import filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from ShahmMusic import BOT_MENTION, BOT_NAME, app
from ShahmMusic.Helpers import gp_buttons, pm_buttons
from ShahmMusic.Helpers.button_style import apply_styles
from ShahmMusic.Helpers.dossier import *


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
            pm_msg = await message.reply_photo(
                photo=config.START_IMG,
                caption=PM_START_TEXT.format(
                    message.from_user.first_name,
                    BOT_MENTION,
                ),
                reply_markup=pm_kb,
            )
            await apply_styles(pm_msg, pm_kb)
    else:
        gp_kb = InlineKeyboardMarkup(gp_buttons)
        gp_msg = await message.reply_photo(
            photo=config.START_IMG,
            caption=START_TEXT.format(
                message.from_user.first_name,
                BOT_MENTION,
                message.chat.title,
                config.SUPPORT_CHAT,
            ),
            reply_markup=gp_kb,
        )
        await apply_styles(gp_msg, gp_kb)
