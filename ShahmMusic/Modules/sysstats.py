
import platform
import re
import socket
import uuid
from sys import version as pyver

import psutil
from pyrogram import __version__ as pyrover
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pytgcalls.__version__ import __version__ as pytgver

from ShahmMusic import BOT_NAME, SUDOERS, app
from ShahmMusic.Helpers.button_style import apply_styles
from ShahmMusic.Modules import ALL_MODULES


@app.on_message(filters.command(["stats", "sysstats"]) | filters.command(["الحاله","الاحصائيات"],prefixes= ["/", "!","","#"]) & SUDOERS)
async def sys_stats(_, message: Message):
    sysrep = await message.reply_text(
        f"{BOT_NAME} اعدادت نضام , سوف يستغرق بعض الوقت ..."
    )
    try:
        await message.delete()
    except:
        pass
    sudoers = len(SUDOERS)
    mod = len(ALL_MODULES)
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(socket.gethostname())
    architecture = platform.machine()
    processor = platform.processor()
    mac_address = ":".join(re.findall("..", "%012x" % uuid.getnode()))
    sp = platform.system()
    ram = str(round(psutil.virtual_memory().total / (1024.0**3))) + " ɢʙ"
    p_core = psutil.cpu_count(logical=False)
    t_core = psutil.cpu_count(logical=True)
    try:
        cpu_freq = psutil.cpu_freq().current
        if cpu_freq >= 1000:
            cpu_freq = f"{round(cpu_freq / 1000, 2)}ɢʜᴢ"
        else:
            cpu_freq = f"{round(cpu_freq, 2)}ᴍʜᴢ"
    except:
        cpu_freq = "ғᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ"
    hdd = psutil.disk_usage("/")
    total = hdd.total / (1024.0**3)
    total = str(total)
    used = hdd.used / (1024.0**3)
    used = str(used)
    free = hdd.free / (1024.0**3)
    free = str(free)
    platform_release = platform.release()
    platform_version = platform.version()

    ss_key = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="مسح",
                    callback_data=f"forceclose abc|{message.from_user.id}",
                ),
            ]
        ]
    )

    await sysrep.edit_text(
        f"""
⌔︙ <u>**{BOT_NAME} احصائيات النظام **</u>

**بايثون :** {pyver.split()[0]}
**بايروجرام :** {pyrover}
**مكالمات بي تي جي :** {pytgver}
**بدثون :** `{sudoers}`
**الوحدات :** `{mod}`

**الايبي :** {ip_address}
**ماك :** {mac_address}
**اسم المضيف :** {hostname}
**منصة :** {sp}
**المعالج :** {processor}
**بنيان :** {architecture}
**إصدار المنصة :** {platform_release}
**إصدار المنصة :** {platform_version}

        <b><u>𝐵𝐷𝑇𝐻𝑂𝑁</b><u/>
**متاح :** {total[:4]} ɢɪʙ
**مستخدم :** {used[:4]} ɢɪʙ
**حر :** {free[:4]} ɢɪʙ

**رام :** {ram}
**النوى المادية :** {p_core}
**مجموع النوى :** {t_core}
**تردد وحدة المعالجة المركزية :** {cpu_freq}""",
        reply_markup=ss_key,
    )
    await apply_styles(sysrep, ss_key)
