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
    
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.ANTIALIAS

    mask = mask.resize(im.size, resample)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)


def get_text_size(draw, text, font):
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
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                result["viewCount"]["short"]
            except:
                pass
            try:
                result["channel"]["name"]
            except:
                pass

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

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        # 1. تجهيز صورة الأغنية/الفيديو كدائرة صغيرة (التي توضع بالأسفل)
        yt_img = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        min_dim_yt = min(yt_img.width, yt_img.height)
        crop_x_yt = (yt_img.width - min_dim_yt) // 2
        crop_y_yt = (yt_img.height - min_dim_yt) // 2
        yt_cropped = yt_img.crop((crop_x_yt, crop_y_yt, crop_x_yt + min_dim_yt, crop_y_yt + min_dim_yt))
        
        mask_circle = Image.new("L", (640, 640), 0)
        draw_circle = ImageDraw.Draw(mask_circle)
        draw_circle.ellipse((0, 0, 640, 640), fill=255)
        
        c = np.array(yt_cropped.resize((640, 640), resample))
        d = np.array(mask_circle)
        e = np.dstack((c[:, :, :3], d))
        x = Image.fromarray(e).resize((107, 107), resample)

        # 2. تجهيز خلفية العرض المظلمة
        image1 = changeImageSize(1280, 720, yt_img)
        background = image1.filter(filter=ImageFilter.BoxBlur(40))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.35)

        # 3. تجهيز صورة المطور/المستخدم كمربع كبير بإطار أبيض جهة اليسار
        user_img = Image.open(wxy).convert("RGBA")
        sq_size = 400
        min_dim_u = min(user_img.width, user_img.height)
        crop_x_u = (user_img.width - min_dim_u) // 2
        crop_y_u = (user_img.height - min_dim_u) // 2
        user_sq = user_img.crop((crop_x_u, crop_y_u, crop_x_u + min_dim_u, crop_y_u + min_dim_u))
        user_sq = user_sq.resize((sq_size, sq_size), resample)

        border_size = sq_size + 20
        bordered_thumb = Image.new("RGBA", (border_size, border_size), "white")
        bordered_thumb.paste(user_sq, (10, 10))

        # دمج صورة المطور المربعة جهة اليسار
        background.paste(bordered_thumb, (90, 150))

        # دمج صورة الفيديو/الأغنية الدائرية في الزاوية السفلى من الغلاف
        background.paste(x, (90 + border_size - 60, 150 + border_size - 60), mask=x)

        draw = ImageDraw.Draw(background)
        font_title = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 40)
        font_sub = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 32)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 26)

        # 4. كتابة النصوص
        x_text = 560
        
        # العنوان العلوي
        draw.text((x_text, 160), "STARTED PLAYING", fill="#00E5FF", font=arial)
        draw.text((x_text, 210), "Shahm Music", fill="#CCCCCC", font=font_sub)

        # اسم الأغنية ينزل في المنطقة السفلى فوق شريط التقدم
        para = textwrap.wrap(title, width=24)
        y_title = 310
        if len(para) > 0 and para[0]:
            draw.text((x_text, y_title), para[0], fill="white", font=font_title)
        if len(para) > 1 and para[1]:
            draw.text((x_text, y_title + 50), para[1], fill="white", font=font_title)

        # 5. شريط التقدم التفاعلي (Progress Bar)
        bar_x1 = x_text
        bar_y = 480
        bar_x2 = 1180

        draw.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill="white", width=4)
        mid_x = bar_x1 + int((bar_x2 - bar_x1) * 0.6)
        draw.ellipse([(mid_x - 10, bar_y - 10), (mid_x + 10, bar_y + 10)], fill="white")

        # التوقيتات تحت الشريط
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
            try:
                result["viewCount"]["short"]
            except:
                pass
            try:
                result["channel"]["name"]
            except:
                pass

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

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        # 1. تجهيز صورة الأغنية كدائرة صغيرة بالأسفل
        yt_img = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        min_dim_yt = min(yt_img.width, yt_img.height)
        crop_x_yt = (yt_img.width - min_dim_yt) // 2
        crop_y_yt = (yt_img.height - min_dim_yt) // 2
        yt_cropped = yt_img.crop((crop_x_yt, crop_y_yt, crop_x_yt + min_dim_yt, crop_y_yt + min_dim_yt))
        
        mask_circle = Image.new("L", (640, 640), 0)
        draw_circle = ImageDraw.Draw(mask_circle)
        draw_circle.ellipse((0, 0, 640, 640), fill=255)
        
        c = np.array(yt_cropped.resize((640, 640), resample))
        d = np.array(mask_circle)
        e = np.dstack((c[:, :, :3], d))
        x = Image.fromarray(e).resize((107, 107), resample)

        # 2. تجهيز الخلفية
        image1 = changeImageSize(1280, 720, yt_img)
        background = image1.filter(filter=ImageFilter.BoxBlur(40))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.35)

        # 3. صورة المطور كمربع كبير بإطار أبيض
        user_img = Image.open(wxy).convert("RGBA")
        sq_size = 400
        min_dim_u = min(user_img.width, user_img.height)
        crop_x_u = (user_img.width - min_dim_u) // 2
        crop_y_u = (user_img.height - min_dim_u) // 2
        user_sq = user_img.crop((crop_x_u, crop_y_u, crop_x_u + min_dim_u, crop_y_u + min_dim_u))
        user_sq = user_sq.resize((sq_size, sq_size), resample)

        border_size = sq_size + 20
        bordered_thumb = Image.new("RGBA", (border_size, border_size), "white")
        bordered_thumb.paste(user_sq, (10, 10))

        background.paste(bordered_thumb, (90, 150))
        background.paste(x, (90 + border_size - 60, 150 + border_size - 60), mask=x)

        draw = ImageDraw.Draw(background)
        font_title = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 40)
        font_sub = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 32)
        arial = ImageFont.truetype("ShahmMusic/Helpers/utils/font2.ttf", 26)

        x_text = 560

        draw.text((x_text, 160), "ADDED TO QUEUE", fill="#FF9800", font=arial)
        draw.text((x_text, 210), "Shahm Music", fill="#CCCCCC", font=font_sub)

        para = textwrap.wrap(title, width=24)
        y_title = 310
        if len(para) > 0 and para[0]:
            draw.text((x_text, y_title), para[0], fill="white", font=font_title)
        if len(para) > 1 and para[1]:
            draw.text((x_text, y_title + 50), para[1], fill="white", font=font_title)

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
