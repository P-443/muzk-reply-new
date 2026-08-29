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


def get_text_size(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)


def make_square_user_photo(image_path, size=(107, 107), radius=15):
    """تجهيز صورة المطور/المستخدم في شكل مربع بحواف منحنية خفيفة"""
    im = Image.open(image_path).convert("RGBA")
    im = im.resize(size, Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS)
    
    # إنشاء ماسك مربع بحواف منحنية
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    output.paste(im, (0, 0), mask=mask)
    return output


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
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            wxy = await app.download_media(
                (await app.get_users(user_id)).photo.big_file_id,
                file_name=f"{user_id}.jpg",
            )
        except:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        # تجهيز صورة المطور/المستخدم كمربع
        user_sq_photo = make_square_user_photo(wxy, size=(110, 110), radius=12)

        # تجهيز الخلفية
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        image1 = changeImageSize(1280, 720, youtube)
        background = image1.filter(filter=ImageFilter.BoxBlur(40))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.35)

        # الغلاف المربع الكبير جهة اليسار
        sq_size = 400
        min_dim = min(youtube.width, youtube.height)
        crop_x = (youtube.width - min_dim) // 2
        crop_y = (youtube.height - min_dim) // 2
        thumb_sq = youtube.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim))
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
        thumb_sq = thumb_sq.resize((sq_size, sq_size), resample)

        border_size = sq_size + 20
        bordered_thumb = Image.new("RGBA", (border_size, border_size), "white")
        bordered_thumb.paste(thumb_sq, (10, 10))

        background.paste(bordered_thumb, (90, 150))
        
        # دمج صورة المطور المربعة في الزاوية السفلى من الغلاف
        background.paste(user_sq_photo, (90 + border_size - 60, 150 + border_size - 60), mask=user_sq_photo)

        draw = ImageDraw.Draw(background)
        font_title = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 40)
        font_sub = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 30)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 26)

        x_text = 560

        # العنوان
        draw.text((x_text, 160), "STARTED PLAYING", fill="#00E5FF", font=font_sub)
        draw.text((x_text, 210), "Shahm Music", fill="#CCCCCC", font=arial)

        # اسم الأغنية تحت (مكان Telegram Files)
        para = textwrap.wrap(title, width=24)
        y_title_start = 310
        
        if len(para) > 0 and para[0]:
            draw.text((x_text, y_title_start), para[0], fill="white", font=font_title)
        if len(para) > 1 and para[1]:
            draw.text((x_text, y_title_start + 50), para[1], fill="white", font=font_title)

        # شريط التقدم
        bar_x1 = x_text
        bar_y = 480
        bar_x2 = 1180

        draw.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill="white", width=4)
        mid_x = bar_x1 + int((bar_x2 - bar_x1) * 0.6)
        draw.ellipse([(mid_x - 10, bar_y - 10), (mid_x + 10, bar_y + 10)], fill="white")

        draw.text((bar_x1, bar_y + 15), "00:00", fill="white", font=arial)
        dur_text = f"{duration} Mins"
        dur_w, _ = get_text_size(draw, dur_text, arial)
        draw.text((bar_x2 - dur_w, bar_y + 15), dur_text, fill="white", font=arial)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
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
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            wxy = await app.download_media(
                (await app.get_users(user_id)).photo.big_file_id,
                file_name=f"{user_id}.jpg",
            )
        except:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        # تجهيز صورة المطور/المستخدم كمربع
        user_sq_photo = make_square_user_photo(wxy, size=(110, 110), radius=12)

        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        image1 = changeImageSize(1280, 720, youtube)
        background = image1.filter(filter=ImageFilter.BoxBlur(40))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.35)

        sq_size = 400
        min_dim = min(youtube.width, youtube.height)
        crop_x = (youtube.width - min_dim) // 2
        crop_y = (youtube.height - min_dim) // 2
        thumb_sq = youtube.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim))
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
        thumb_sq = thumb_sq.resize((sq_size, sq_size), resample)

        border_size = sq_size + 20
        bordered_thumb = Image.new("RGBA", (border_size, border_size), "white")
        bordered_thumb.paste(thumb_sq, (10, 10))

        background.paste(bordered_thumb, (90, 150))
        
        # دمج صورة المطور المربعة
        background.paste(user_sq_photo, (90 + border_size - 60, 150 + border_size - 60), mask=user_sq_photo)

        draw = ImageDraw.Draw(background)
        font_title = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 40)
        font_sub = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 30)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 26)

        x_text = 560

        draw.text((x_text, 160), "ADDED TO QUEUE", fill="#FF9800", font=font_sub)
        draw.text((x_text, 210), "Shahm Music", fill="#CCCCCC", font=arial)

        para = textwrap.wrap(title, width=24)
        y_title_start = 310
        
        if len(para) > 0 and para[0]:
            draw.text((x_text, y_title_start), para[0], fill="white", font=font_title)
        if len(para) > 1 and para[1]:
            draw.text((x_text, y_title_start + 50), para[1], fill="white", font=font_title)

        bar_x1 = x_text
        bar_y = 480
        bar_x2 = 1180

        draw.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill="white", width=4)
        mid_x = bar_x1 + int((bar_x2 - bar_x1) * 0.6)
        draw.ellipse([(mid_x - 10, bar_y - 10), (mid_x + 10, bar_y + 10)], fill="white")

        draw.text((bar_x1, bar_y + 15), "00:00", fill="white", font=arial)
        dur_text = f"{duration} Mins"
        dur_w, _ = get_text_size(draw, dur_text, arial)
        draw.text((bar_x2 - dur_w, bar_y + 15), dur_text, fill="white", font=arial)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
