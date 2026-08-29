
from pyrogram import filters
from pyrogram.types import Message

from ShahmMusic import app, pytgcalls
from ShahmMusic.Helpers import admin_check, close_key, is_streaming, stream_on
from ShahmMusic.Helpers.button_style import HEADPHONE_TAG, apply_styles


@app.on_message(filters.command(["resume"]) | filters.command(["كمل","الغاء كتم","الغاء الكتم","اتكلم"],prefixes= ["/", "!","","#"]) & filters.group)
@admin_check
async def res_str(_, message: Message):
    try:
        await message.delete()
    except:
        pass

    if await is_streaming(message.chat.id):
        return await message.reply_text("** انت وقفتني ارسل كمل لاكمال الاغنيه**")
    await stream_on(message.chat.id)
    await pytgcalls.resume_stream(message.chat.id)
    rmsg = await message.reply_text(
        text=f"⌔︙ تم استئناف التشغيل {HEADPHONE_TAG}\n \n⌔︙ بواسطة : {message.from_user.mention} ",
        reply_markup=close_key,
    )
    await apply_styles(rmsg, close_key)
