
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup
from pytgcalls.types import AudioPiped, HighQualityAudio

from ShahmMusic import (
    ASS_ID,
    ASS_NAME,
    BOT_ID,
    BOT_MENTION,
    BOT_USERNAME,
    LOGGER,
    app,
    Shahmdb,
    pytgcalls,
)
from ShahmMusic.Helpers import (
    _clear_,
    admin_check_cb,
    gen_thumb,
    is_streaming,
    stream_off,
    stream_on,
)
from ShahmMusic.Helpers.button_style import apply_styles
from ShahmMusic.Helpers.dossier import *
from ShahmMusic.Helpers.inline import (
    buttons,
    close_key,
    help_back,
    helpmenu,
    pm_buttons,
)


@app.on_callback_query(filters.regex("forceclose"))
async def close_(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    query, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(
                "⌔︙ اعرف حدودك حبيبي لو اعلمك بيها.", show_alert=True
            )
        except:
            return
    await CallbackQuery.message.delete()
    try:
        await CallbackQuery.answer()
    except:
        return


@app.on_callback_query(filters.regex("close"))
async def forceclose_command(_, CallbackQuery):
    try:
        await CallbackQuery.message.delete()
    except:
        return
    try:
        await CallbackQuery.answer()
    except:
        pass


@app.on_callback_query(filters.regex(pattern=r"^(resume_cb|pause_cb|skip_cb|end_cb)$"))
@admin_check_cb
async def admin_cbs(_, query: CallbackQuery):
    try:
        await query.answer()
    except:
        pass

    data = query.matches[0].group(1)

    if data == "resume_cb":
        if await is_streaming(query.message.chat.id):
            return await query.answer(
                "شنو تذكرت تستأنف البث ?", show_alert=True
            )
        await stream_on(query.message.chat.id)
        await pytgcalls.resume_stream(query.message.chat.id)
        rmsg = await query.message.reply_text(
            text=f"⌔︙ تم استئناف التشغيل ⚡\n \n⌔︙ بواسطة : {query.from_user.mention} ",
            reply_markup=close_key,
        )
        await apply_styles(rmsg, close_key)

    elif data == "pause_cb":
        if not await is_streaming(query.message.chat.id):
            return await query.answer(
                "ᴅɪᴅ ʏᴏᴜ ʀᴇᴍᴇᴍʙᴇʀ ᴛʜᴀᴛ ʏᴏᴜ ʀᴇsᴜᴍᴇᴅ ᴛʜᴇ sᴛʀᴇᴀᴍ ?", show_alert=True
            )
        await stream_off(query.message.chat.id)
        await pytgcalls.pause_stream(query.message.chat.id)
        pmsg = await query.message.reply_text(
            text=f"⌔︙ تم ايقاف التشغيل مؤقتاً \n \n⌔︙ بواسطة : {query.from_user.mention} ",
            reply_markup=close_key,
        )
        await apply_styles(pmsg, close_key)

    elif data == "end_cb":
        try:
            await _clear_(query.message.chat.id)
            await pytgcalls.leave_group_call(query.message.chat.id)
        except:
            pass
        smsg = await query.message.reply_text(
            text=f"⌔︙ تم ايقاف التشغيل \n \n⌔︙ بواسطة : {query.from_user.mention}",
            reply_markup=close_key,
        )
        await apply_styles(smsg, close_key)
        await query.message.delete()

    elif data == "skip_cb":
        get = Shahmdb.get(query.message.chat.id)
        if not get:
            try:
                await _clear_(query.message.chat.id)
                await pytgcalls.leave_group_call(query.message.chat.id)
                nmsg = await query.message.reply_text(
                    text=f"⌔︙ تخطي الاغنية \n \n⌔︙ بواسطة : {query.from_user.mention} \n\n**⌔︙ لا يوجد اغنية تالية في قائمة الانتظار ** {query.message.chat.title}, **ترك دردشة الفيديو**",
                    reply_markup=close_key,
                )
                await apply_styles(nmsg, close_key)
                return await query.message.delete()
            except:
                return
        else:
            title = get[0]["title"]
            duration = get[0]["duration"]
            videoid = get[0]["videoid"]
            file_path = get[0]["file_path"]
            req_by = get[0]["req"]
            user_id = get[0]["user_id"]
            get.pop(0)

            stream = AudioPiped(file_path, audio_parameters=HighQualityAudio())
            try:
                await pytgcalls.change_stream(
                    query.message.chat.id,
                    stream,
                )
            except Exception as ex:
                LOGGER.error(ex)
                await _clear_(query.message.chat.id)
                return await pytgcalls.leave_group_call(query.message.chat.id)

            img = await gen_thumb(videoid, user_id)
            emsg = await query.edit_message_text(
                text=f"⌔︙ تم تخطي التشغيل \n \n⌔︙ بواسطة : {query.from_user.mention}",
                reply_markup=close_key,
            )
            await apply_styles(emsg, close_key)
            skmsg = await query.message.reply_photo(
                photo=img,
                caption=f"**⌔︙ بدء تشغيل**\n\n⌔︙ **العنوان :** [{title[:27]}](https://t.me/{BOT_USERNAME}?start=info_{videoid})\n⌔︙ **المدة :** `{duration}` دقيقة\n⌔︙ **مطلوبة من :** {req_by}",
                reply_markup=buttons,
            )
            await apply_styles(skmsg, buttons)


@app.on_callback_query(filters.regex("unban_ass"))
async def unban_ass(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    chat_id, user_id = callback_request.split("|")
    umm = (await app.get_chat_member(int(chat_id), BOT_ID)).privileges
    if umm.can_restrict_members:
        try:
            await app.unban_chat_member(int(chat_id), ASS_ID)
        except:
            return await CallbackQuery.answer(
                "⌔︙ فشل الحساب المساعد محظور",
                show_alert=True,
            )
        return await CallbackQuery.edit_message_text(
            f"⌔︙ {ASS_NAME} تم رفع الحظر بنجاح بواسطة {CallbackQuery.from_user.mention}.\n\⌔︙ البوت يعمل الان ⚡"
        )
    else:
        return await CallbackQuery.answer(
            "⌔︙ ليس لدي أذونات لإلغاء حظر المستخدمين في هذه الدردشة ",
            show_alert=True,
        )


@app.on_callback_query(filters.regex("Shahm_help"))
async def help_menu(_, query: CallbackQuery):
    try:
        await query.answer()
    except:
        pass

    try:
        help_msg = await query.edit_message_text(
            text=f"⌔︙ مرحبا {query.from_user.first_name} \n\n⌔︙ اختر من الازرار في الاسفل ⬇️ ",
            reply_markup=InlineKeyboardMarkup(helpmenu),
        )
        await apply_styles(help_msg, InlineKeyboardMarkup(helpmenu))
    except Exception as e:
        LOGGER.error(e)
        return


@app.on_callback_query(filters.regex("Shahm_cb"))
async def open_hmenu(_, query: CallbackQuery):
    callback_data = query.data.strip()
    cb = callback_data.split(None, 1)[1]
    keyboard = InlineKeyboardMarkup(help_back)

    try:
        await query.answer()
    except:
        pass

    hmsg = None
    if cb == "help":
        hmsg = await query.edit_message_text(HELP_TEXT, reply_markup=keyboard)
    elif cb == "sudo":
        hmsg = await query.edit_message_text(HELP_SUDO, reply_markup=keyboard)
    elif cb == "owner":
        hmsg = await query.edit_message_text(HELP_DEV, reply_markup=keyboard)
    if hmsg is not None:
        await apply_styles(hmsg, keyboard)


@app.on_callback_query(filters.regex("Shahm_home"))
async def home_Shahm(_, query: CallbackQuery):
    try:
        await query.answer()
    except:
        pass
    try:
        hm_msg = await query.edit_message_text(
            text=PM_START_TEXT.format(
                query.from_user.first_name,
                BOT_MENTION,
            ),
            reply_markup=InlineKeyboardMarkup(pm_buttons),
        )
        await apply_styles(hm_msg, InlineKeyboardMarkup(pm_buttons))
    except:
        pass
