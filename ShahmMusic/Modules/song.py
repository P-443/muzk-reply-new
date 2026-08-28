
import os

import requests
import yt_dlp
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from ShahmMusic.Helpers.downloaders import yt_search

from ShahmMusic import BOT_MENTION, BOT_USERNAME, LOGGER, app


@app.on_message(filters.command(["song", "vsong", "video", "music"]) | filters.command(["بحث","تنزيل","نزل"],prefixes= ["/", "!","","#"]))
async def song(_, message: Message):
    try:
        await message.delete()
    except:
        pass
    m = await message.reply_text("⌔︙ جارٍ التحميل...")

    query = "".join(" " + str(i) for i in message.command[1:])
    cookie_file = os.getenv("YTDLP_COOKIES")
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "visionos", "tv_downgraded", "tv", "web_embedded"],
            }
        },
    }
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts["cookiefile"] = cookie_file
        ydl_opts["extractor_args"]["youtube"]["player_client"] = [
            "web",
            "visionos",
            "tv",
            "web_embedded",
        ]
    try:
        results = yt_search(query, 1)
        if not results:
            raise Exception("لا توجد نتائج للبحث")
        link = f"https://youtube.com{results[0]['url_suffix']}"
        title = results[0]["title"][:40]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
        duration = results[0]["duration"]

    except Exception as ex:
        LOGGER.error(ex)
        return await m.edit_text(
            f"فشل إحضار المسار من ʏᴛ-ᴅʟ.\n\n**السبب :** `{ex}`"
        )

    await m.edit_text("**⌔︙ يتم التحميل **\n\n**⌔︙ من فضلك انتظر")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)
            audio_file = ydl.prepare_filename(info_dict)
            ydl.process_info(info_dict)
        rep = f"⌔︙ **العنوان :** [{title[:23]}]({link})\n⌔︙ **المده :** `{duration}`\n⌔︙ ** بواسطة :** {BOT_MENTION}"
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(dur_arr[i]) * secmul
            secmul *= 60
        try:
            visit_butt = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="‹ رابط يوتيوب ›",
                            url=link,
                        )
                    ]
                ]
            )
            await app.send_audio(
                chat_id=message.from_user.id,
                audio=audio_file,
                caption=rep,
                thumb=thumb_name,
                title=title,
                duration=dur,
                reply_markup=visit_butt,
            )
            if message.chat.type != ChatType.PRIVATE:
                await message.reply_text(
                    "يرجى التحقق من أن المسؤول قد أرسل الأغنية المطلوبة."
                )
        except:
            start_butt = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="اضغط هنا",
                            url=f"https://t.me/{BOT_USERNAME}?start",
                        )
                    ]
                ]
            )
            return await m.edit_text(
                text="اضغط فوق الزر أدناه وابدأ في تنزيل الأغاني",
                reply_markup=start_butt,
            )
        await m.delete()
    except:
        return await m.edit_text("فشل تحميل الصوت على الخادم")

    try:
        os.remove(audio_file)
        os.remove(thumb_name)
    except Exception as ex:
        LOGGER.error(ex)
