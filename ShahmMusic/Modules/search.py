
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from ShahmMusic.Helpers.downloaders import yt_search

from ShahmMusic import app


@app.on_message(filters.command(["search"]) | filters.command(["بحث","يوت"],prefixes= ["/", "!","","#"]))
async def ytsearch(_, message: Message):
    try:
        await message.delete()
    except:
        pass
    try:
        if len(message.command) < 2:
            return await message.reply_text("⌔︙ اكتب شي تريد تبحث علي")
        query = message.text.split(None, 1)[1]
        m = await message.reply_text("⌔︙ جارٍ البحث...")
        results = yt_search(query, 4)
        text = ""
        for r in results[:4]:
            text += f"⌔︙ العنوان : {r['title']}\n"
            text += f"⌔︙ المدة : `{r['duration']}`\n"
            text += f"⌔︙ المشاهدات : `{r['views']}`\n"
            text += f"⌔︙ القناه : {r['channel']}\n"
            text += f"⌔︙ الرابط : https://youtube.com{r['url_suffix']}\n\n"
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="اقفل",
                        callback_data=f"forceclose abc|{message.from_user.id}",
                    ),
                ]
            ]
        )
        await m.edit_text(
            text=text,
            reply_markup=key,
            disable_web_page_preview=True,
        )
    except Exception as e:
        await message.reply_text(str(e))
