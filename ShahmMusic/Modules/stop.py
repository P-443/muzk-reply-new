
from pyrogram import filters
from pyrogram.types import Message

from ShahmMusic import app, pytgcalls
from ShahmMusic.Helpers import _clear_, admin_check, close_key
from ShahmMusic.Helpers.button_style import apply_styles


@app.on_message(filters.command(["stop", "end"]) | filters.command(["ايقاف","اسكت"],prefixes= ["/", "!","","#"]) & filters.group)
@admin_check
async def stop_str(_, message: Message):
    try:
        await message.delete()
    except:
        pass
    try:
        await _clear_(message.chat.id)
        await pytgcalls.leave_group_call(message.chat.id)
    except:
        pass

    stop_msg = await message.reply_text(
        text=f"⌔︙ **تم ايقاف التشغيل** \n \n⌔︙ بواسطة : {message.from_user.mention} ",
        reply_markup=close_key,
    )
    await apply_styles(stop_msg, close_key)
