
from pyrogram import filters
from pyrogram.types import Message

from ShahmMusic import SUDOERS, app
from ShahmMusic.Helpers.active import get_active_chats
from ShahmMusic.Helpers.button_style import THUNDER_TAG, apply_styles
from ShahmMusic.Helpers.inline import close_key


@app.on_message(filters.command("activevc") | filters.command(["المكالمات","النشطه"],prefixes= ["/", "!","","#"]) & SUDOERS)
async def activevc(_, message: Message):
    mystic = await message.reply_text(f"⌔︙ جاري جلب المكالمات {THUNDER_TAG}")
    chats = await get_active_chats()
    text = ""
    j = 0
    for chat in chats:
        try:
            title = (await app.get_chat(chat)).title
        except Exception:
            title = "المكالمات الخاصة"
        if (await app.get_chat(chat)).username:
            user = (await app.get_chat(chat)).username
            text += f"<b>{j + 1}.</b>  [{title}](https://t.me/{user})\n"
        else:
            text += f"<b>{j + 1}. {title}</b> [`{x}`]\n"
        j += 1
    if not text:
        await mystic.edit_text("⌔︙ لا يـوجد مكالمات في الوقت الحالي")
    else:
        avc_msg = await mystic.edit_text(
            f"**قائمة المكالمات الشغالة :**\n\n{text}",
            reply_markup=close_key,
            disable_web_page_preview=True,
        )
        await apply_styles(avc_msg, close_key)
