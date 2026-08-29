import os
import re
import textwrap

import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

from config import FAILED
from ShahmMusic import BOT_ID, LOGGER, app


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))


def add_corners(im):
    bigsize = (im.size[0] * 3, im.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
    
    # دعم الإصدارات الحديثة من Pillow لفرز الحواف
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.ANTIALIAS

    mask = mask.resize(im.size, resample)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)


def get_text_size(draw, text, font):
    """دالة مساعدة لمعرفة أبعاد النص بما يتوافق مع جميع إصدارات Pillow."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)


async def gen_thumb(videoid, user_id):
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"
        
    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub(r"\W+", " ", title).strip().title()
            except Exception:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except Exception:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        try:
            wxy = await app.download_media(
                (await app.get_users(user_id)).photo.big_file_id,
                file_name=f"{user_id}.jpg",
            )
        except Exception:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        xy = Image.open(wxy)
        a = Image.new("L", [640, 640], 0)
        b = ImageDraw.Draw(a)
        b.pieslice([(0, 0), (640, 640)], 0, 360, fill=255, outline="white")
        c = np.array(xy)
        d = np.array(a)
        e = np.dstack((c, d))
        f = Image.fromarray(e)
        x = f.resize((107, 107))

        youtube = Image.open(f"cache/thumb{videoid}.png")
        
        # تجهيز الخلفية مع التمويه
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(30))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.6)

        # تحضير اللوجو/الغلاف الدائري
        Xcenter = youtube.width / 2
        Ycenter = youtube.height / 2
        x1 = Xcenter - 250
        y1 = Ycenter - 250
        x2 = Xcenter + 250
        y2 = Ycenter + 250
        logo = youtube.crop((x1, y1, x2, y2))
        logo.thumbnail((520, 520), resample)
        logo.save(f"cache/chop{videoid}.png")

        if not os.path.isfile(f"cache/cropped{videoid}.png"):
            im = Image.open(f"cache/chop{videoid}.png").convert("RGBA")
            add_corners(im)
            im.save(f"cache/cropped{videoid}.png")

        crop_img = Image.open(f"cache/cropped{videoid}.png")
        logo = crop_img.convert("RGBA")
        logo.thumbnail((365, 365), resample)
        width = int((1280 - 365) / 2)

        # دمج الطبقات
        if os.path.isfile("ShahmMusic/Helpers/utils/circle.png"):
            bg = Image.open("ShahmMusic/Helpers/utils/circle.png")
            image3 = changeImageSize(1280, 720, bg).convert("RGBA")
            background.paste(logo, (width + 2, 138), mask=logo)
            background.paste(x, (710, 427), mask=x)
            background.paste(image3, (0, 0), mask=image3)
        else:
            background.paste(logo, (width + 2, 138), mask=logo)
            background.paste(x, (710, 427), mask=x)

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 45)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 30)

        # عنوان التشغيل
        head_text = "STARTED PLAYING"
        head_w, _ = get_text_size(draw, head_text, font)
        draw.text(
            ((1280 - head_w) / 2, 25),
            head_text,
            fill="white",
            stroke_width=3,
            stroke_fill="grey",
            font=font,
        )

        # عنوان الأغنية
        para = textwrap.wrap(title, width=32)
        if len(para) > 0 and para[0]:
            text_w, _ = get_text_size(draw, para[0], font)
            draw.text(
                ((1280 - text_w) / 2, 530),
                para[0],
                fill="white",
                stroke_width=1,
                stroke_fill="white",
                font=font,
            )
        if len(para) > 1 and para[1]:
            text_w, _ = get_text_size(draw, para[1], font)
            draw.text(
                ((1280 - text_w) / 2, 580),
                para[1],
                fill="white",
                stroke_width=1,
                stroke_fill="white",
                font=font,
            )

        # مدة الأغنية
        dur_text = f"Duration: {duration} Mins"
        text_w, _ = get_text_size(draw, dur_text, arial)
        draw.text(
            ((1280 - text_w) / 2, 660),
            dur_text,
            fill="white",
            font=arial,
        )

        # تنظيف الملفات المؤقتة
        for temp_file in [f"cache/thumb{videoid}.png", f"cache/chop{videoid}.png", f"cache/cropped{videoid}.png"]:
            if os.path.isfile(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        background.save(f"cache/{videoid}_{user_id}.png")
        return f"cache/{videoid}_{user_id}.png"

    except Exception as e:
        LOGGER.error(e)
        return FAILED


async def gen_qthumb(videoid, user_id):
    if os.path.isfile(f"cache/que{videoid}_{user_id}.png"):
        return f"cache/que{videoid}_{user_id}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub(r"\W+", " ", title).strip().title()
            except Exception:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except Exception:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        try:
            wxy = await app.download_media(
                (await app.get_users(user_id)).photo.big_file_id,
                file_name=f"{user_id}.jpg",
            )
        except Exception:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        xy = Image.open(wxy)
        a = Image.new("L", [640, 640], 0)
        b = ImageDraw.Draw(a)
        b.pieslice([(0, 0), (640, 640)], 0, 360, fill=255, outline="white")
        c = np.array(xy)
        d = np.array(a)
        e = np.dstack((c, d))
        f = Image.fromarray(e)
        x = f.resize((107, 107))

        youtube = Image.open(f"cache/thumb{videoid}.png")
        
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(30))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.6)

        Xcenter = youtube.width / 2
        Ycenter = youtube.height / 2
        x1 = Xcenter - 250
        y1 = Ycenter - 250
        x2 = Xcenter + 250
        y2 = Ycenter + 250
        logo = youtube.crop((x1, y1, x2, y2))
        logo.thumbnail((520, 520), resample)
        logo.save(f"cache/chop{videoid}.png")

        if not os.path.isfile(f"cache/cropped{videoid}.png"):
            im = Image.open(f"cache/chop{videoid}.png").convert("RGBA")
            add_corners(im)
            im.save(f"cache/cropped{videoid}.png")

        crop_img = Image.open(f"cache/cropped{videoid}.png")
        logo = crop_img.convert("RGBA")
        logo.thumbnail((365, 365), resample)
        width = int((1280 - 365) / 2)

        if os.path.isfile("ShahmMusic/Helpers/utils/circle.png"):
            bg = Image.open("ShahmMusic/Helpers/utils/circle.png")
            image3 = changeImageSize(1280, 720, bg).convert("RGBA")
            background.paste(logo, (width + 2, 138), mask=logo)
            background.paste(x, (710, 427), mask=x)
            background.paste(image3, (0, 0), mask=image3)
        else:
            background.paste(logo, (width + 2, 138), mask=logo)
            background.paste(x, (710, 427), mask=x)

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 45)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 30)

        # عنوان قائمة الانتظار
        head_text = "ADDED TO QUEUE"
        head_w, _ = get_text_size(draw, head_text, font)
        draw.text(
            ((1280 - head_w) / 2, 25),
            head_text,
            fill="white",
            stroke_width=5,
            stroke_fill="black",
            font=font,
        )

        # عنوان الأغنية
        para = textwrap.wrap(title, width=32)
        if len(para) > 0 and para[0]:
            text_w, _ = get_text_size(draw, para[0], font)
            draw.text(
                ((1280 - text_w) / 2, 530),
                para[0],
                fill="white",
                stroke_width=1,
                stroke_fill="white",
                font=font,
            )
        if len(para) > 1 and para[1]:
            text_w, _ = get_text_size(draw, para[1], font)
            draw.text(
                ((1280 - text_w) / 2, 580),
                para[1],
                fill="white",
                stroke_width=1,
                stroke_fill="white",
                font=font,
            )

        # مدة الأغنية
        dur_text = f"Duration: {duration} Mins"
        text_w, _ = get_text_size(draw, dur_text, arial)
        draw.text(
            ((1280 - text_w) / 2, 660),
            dur_text,
            fill="white",
            font=arial,
        )

        # تنظيف الملفات المؤقتة
        for temp_file in [f"cache/thumb{videoid}.png", f"cache/chop{videoid}.png", f"cache/cropped{videoid}.png"]:
            if os.path.isfile(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"

    except Exception as e:
        LOGGER.error(e)
        return FAILED
