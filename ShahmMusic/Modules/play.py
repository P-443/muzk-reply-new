
import asyncio
import os

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    ChatAdminRequired,
    UserAlreadyParticipant,
    UserNotParticipant,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pytgcalls import StreamType
from pytgcalls.exceptions import NoActiveGroupCall, TelegramServerError, UnMuteNeeded
from pytgcalls.types import AudioPiped, HighQualityAudio

from config import DURATION_LIMIT
from ShahmMusic import (
    ASS_ID,
    ASS_MENTION,
    ASS_NAME,
    ASS_USERNAME,
    BOT_NAME,
    BOT_USERNAME,
    LOGGER,
    app,
    app2,
    Shahmdb,
    pytgcalls,
)
from ShahmMusic.Helpers.active import add_active_chat, is_active_chat, stream_on
from ShahmMusic.Helpers.button_style import apply_styles
from ShahmMusic.Helpers.downloaders import audio_dl, yt_search
from ShahmMusic.Helpers.errors import DurationLimitError
from ShahmMusic.Helpers.gets import get_file_name, get_url
from ShahmMusic.Helpers.inline import buttons
from ShahmMusic.Helpers.queue import put
from ShahmMusic.Helpers.thumbnails import gen_qthumb, gen_thumb


@app.on_message(
    filters.command(["play", "شغل", "تشغيل"]) | filters.command(["تشغيل","شغل","ش"],prefixes= ["/", "!","","#"])
    & ~filters.forwarded
    & ~filters.via_bot
)
async def play(_, message: Message):
    Shahm = await message.reply_text("** جاري التشغيل...**")
    try:
        await message.delete()
    except:
        pass

    try:
        try:
            get = await app.get_chat_member(message.chat.id, ASS_ID)
        except ChatAdminRequired:
            return await Shahm.edit_text(
                f"  ** اعطني صلاحية الاضافة ليتم اضافة المساعد** {BOT_NAME} ** وحاول مرة اخرى {message.chat.title}."
            )
        if get.status == ChatMemberStatus.BANNED:
            unban_butt = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=f"الغاء حظر {ASS_NAME}",
                            callback_data=f"unban_assistant {message.chat.id}|{ASS_ID}",
                        ),
                    ]
                ]
            )
            unban_msg = await Shahm.edit_text(
                text=f"⌔︙ {BOT_NAME} الحساب المساعد محظور في {message.chat.title}\n\n⌔︙ الايدي : `{ASS_ID}`\n⌔︙ آلآسم : {ASS_MENTION}\n⌔︙ اليوزر : @{ASS_USERNAME}\n\n⌔︙ الغي حظر الحساب المساعد...",
                reply_markup=unban_butt,
            )
            await apply_styles(unban_msg, unban_butt)
            return
    except UserNotParticipant:
        if message.chat.username:
            invitelink = message.chat.username
            try:
                await app2.resolve_peer(invitelink)
            except Exception as ex:
                LOGGER.error(ex)
        else:
            try:
                invitelink = await app.export_chat_invite_link(message.chat.id)
            except ChatAdminRequired:
                return await Shahm.edit_text(
                    f"⌔︙ ** اعطني صلاحية الاضافة ليتم اضافة المساعد**{BOT_NAME} ** وحاول مره اخرى** {message.chat.title}."
                )
            except Exception as ex:
                return await Shahm.edit_text(
                    f"فشلت الدعوة {BOT_NAME} المساعد {message.chat.title}.\n\n**آلسبب :** `{ex}`"
                )
        if invitelink.startswith("https://t.me/+"):
            invitelink = invitelink.replace("https://t.me/+", "https://t.me/joinchat/")
        anon = await Shahm.edit_text(
            f"⌔︙ انتظر من فضلك يتم اضافة حساب المساعد\n\n {ASS_NAME} في {message.chat.title}."
        )
        try:
            await app2.join_chat(invitelink)
            await asyncio.sleep(2)
            await Shahm.edit_text(
                f"{ASS_NAME} **  دخلت يا صحبي ✅,\n\n بدء التشغيل..."
            )
        except UserAlreadyParticipant:
            pass
        except Exception as ex:
            return await Shahm.edit_text(
                f"فشلت الدعوة {BOT_NAME} حاول مرة اخرى ** {message.chat.title}.\n\n**السبب :** `{ex}`"
            )
        try:
            await app2.resolve_peer(invitelink)
        except:
            pass

    ruser = message.from_user.first_name
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    url = get_url(message)
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"⌔︙ فشل التشغيل بسبب ان الاغنية طويلة {DURATION_LIMIT} شغل اغنية اخرى {BOT_NAME}."
            )

        file_name = get_file_name(audio)
        title = file_name
        duration = round(audio.duration / 60)
        file_path = (
            await message.reply_to_message.download(file_name)
            if not os.path.isfile(os.path.join("downloads", file_name))
            else f"downloads/{file_name}"
        )

    elif url:
        try:
            results = yt_search(url, 1)
            title = results[0]["title"]
            duration = results[0]["duration"]
            videoid = results[0]["id"]

            secmul, dur, dur_arr = 1, 0, duration.split(":")
            for i in range(len(dur_arr) - 1, -1, -1):
                dur += int(dur_arr[i]) * secmul
                secmul *= 60

        except Exception as e:
            return await Shahm.edit_text(f"هناك خطأ\n\n**ايرور :** `{e}`")

        if (dur / 60) > DURATION_LIMIT:
            return await Shahm.edit_text(
                f"⌔︙ فشل التشغيل بسبب ان الاغنية طويلة {DURATION_LIMIT} شغل اغنية تانية {BOT_NAME}.."
            )
        file_path = audio_dl(url)
    else:
        if len(message.command) < 2:
            return await Shahm.edit_text("⌔︙ اكتب اسم الاغنية 🎧")
        await Shahm.edit_text("⚡️")
        query = message.text.split(None, 1)[1]
        try:
            results = yt_search(query, 1)
            url = f"https://youtube.com{results[0]['url_suffix']}"
            title = results[0]["title"]
            videoid = results[0]["id"]
            duration = results[0]["duration"]

            secmul, dur, dur_arr = 1, 0, duration.split(":")
            for i in range(len(dur_arr) - 1, -1, -1):
                dur += int(dur_arr[i]) * secmul
                secmul *= 60

        except Exception as e:
            LOGGER.error(str(e))
            return await Shahm.edit("⌔︙ فشل في المعالجة جرب مرة أخرى...")

        if (dur / 60) > DURATION_LIMIT:
            return await Shahm.edit(
                f"⌔︙ فشل التشغيل بسبب ان الاغنية طويلة {DURATION_LIMIT} شغل اغنية تانية {BOT_NAME}.."
            )
        file_path = audio_dl(url)

    try:
        videoid = videoid
    except:
        videoid = "fuckitstgaudio"
    if await is_active_chat(message.chat.id):
        await put(
            message.chat.id,
            title,
            duration,
            videoid,
            file_path,
            ruser,
            message.from_user.id,
        )
        position = len(Shahmdb.get(message.chat.id))
        qimg = await gen_qthumb(videoid, message.from_user.id)
        qmsg = await message.reply_photo(
            photo=qimg,
            caption=f"**⌔︙ تمت الإضافة إلى قائمة الانتظار في {position}**\n\n⌔︙ **العنوان :** [{title[:27]}](https://t.me/{BOT_USERNAME}?start=info_{videoid})\n⌔︙ **المده :** `{duration}` دقيقه\n⌔︙ **مطلوب بواسطة :** {ruser}",
            reply_markup=buttons,
        )
        await apply_styles(qmsg, buttons)
    else:
        stream = AudioPiped(file_path, audio_parameters=HighQualityAudio())
        try:
            await pytgcalls.join_group_call(
                message.chat.id,
                stream,
                stream_type=StreamType().pulse_stream,
            )

        except NoActiveGroupCall:
            return await Shahm.edit_text(
                "**⌔︙ افتح المكالمة الصوتية اولاً ** يرجى التأكد من فتح محادثة الفيديو"
            )
        except TelegramServerError:
            return await Shahm.edit_text(
                "** ⌔︙ حدثت مشكلة اغلق الاتصال وحاول مرة اخرى**"
            )
        except UnMuteNeeded:
            return await Shahm.edit_text(
                f"⌔︙ {BOT_NAME} الحساب المساعد مكتوم,\n\nالرجاء فك كتم الحساب المساعد {ASS_MENTION} و المحاوله مرة اخري"
            )

        imgt = await gen_thumb(videoid, message.from_user.id)
        await stream_on(message.chat.id)
        await add_active_chat(message.chat.id)
        pmsg = await message.reply_photo(
            photo=imgt,
            caption=f"**⌔︙ تم التشغيل 🎧**\n\n⌔︙ **العنوان :** [{title[:27]}](https://t.me/{BOT_USERNAME}?start=info_{videoid})\n⌔︙ **المده :** `{duration}` دقيقه\n⌔︙ **بواسطه :** {ruser}",
            reply_markup=buttons,
        )
        await apply_styles(pmsg, buttons)

    return await Shahm.delete()
