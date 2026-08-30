import os
import re
import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
import arabic_reshaper
from bidi.algorithm import get_display

from config import FAILED, OWNER_ID
from ShahmMusic import BOT_ID, LOGGER, app


def fix_arabic_text(text, max_chars=0):
    if not text:
        return ""
    try:
        if max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars] + "..."
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        LOGGER.error(f"Error shaping arabic text: {e}")
        return text


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))


def make_circular_crop(img):
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result


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
            title = result.get("title", "Unsupported Title")
            duration = result.get("duration", "Unknown")
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            owner_user = await app.get_users(OWNER_ID)
            wxy = await app.download_media(
                owner_user.photo.big_file_id,
                file_name=f"owner_{OWNER_ID}.jpg",
            )
        except Exception:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        try:
            req_user = await app.get_users(user_id)
            user_tag = f"@{req_user.username}" if req_user.username else req_user.first_name
        except:
            user_tag = "User"

        resample = getattr(Image.Resampling, "LANCZOS", Image.ANTIALIAS)

        # 1. إنشاء خلفية سوداء بالكامل 1280x720 (Flat Dark Canvas)
        canvas = Image.new("RGBA", (1280, 720), (12, 12, 16, 255))

        # 2. النص الأيسر: صورة اليوتيوب واضحة جداً بدون Blur
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        yt_resized = changeImageSize(600, 720, youtube)
        
        # قص الصورة لضبط المقاس ووضعها في الجانب الأيسر
        yt_crop = yt_resized.crop((0, 0, min(600, yt_resized.width), 720))
        canvas.paste(yt_crop, (0, 0))

        # خط فاصل رأس المظهر الفخم (Neon Crimson Separator)
        draw = ImageDraw.Draw(canvas)
        draw.line([(600, 0), (600, 720)], fill="#E50914", width=5)

        # 3. النص الأيمن: صورة المطور على شكل بادتج (Developer Badge) في الزاوية
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 120
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_circle = make_circular_crop(owner_sq)

        # وضع صورة المطور أسفل اليمين
        canvas.paste(owner_circle, (1110, 560), mask=owner_circle)
        draw.ellipse([(1108, 558), (1232, 682)], fill=None, outline="#E50914", width=3)

        # 4. تحميل الخطوط
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 40)
            font_sub = ImageFont.truetype(font_path, 28)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        # 5. كتابة البيانات على الجانب الأيمن النظيف
        x_start = 650

        # شريط الحالة
        draw.text((x_start, 120), "● NOW PLAYING", fill="#E50914", font=font_small)

        # اسم المقطع
        formatted_title = fix_arabic_text(title, max_chars=20)
        draw.text((x_start, 180), formatted_title, fill="#FFFFFF", font=font_title)

        # صاحب الطلب
        req_text = fix_arabic_text(f"Requested by: {user_tag}", max_chars=24)
        draw.text((x_start, 260), req_text, fill="#A0A0A0", font=font_sub)

        # 6. شريط التشغيل المودرن
        bar_y = 420
        bar_x2 = 1220

        draw.line([(x_start, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=6)
        progress_x = x_start + int((bar_x2 - x_start) * 0.40)
        draw.line([(x_start, bar_y), (progress_x, bar_y)], fill="#E50914", width=6)
        draw.ellipse([(progress_x - 8, bar_y - 8), (progress_x + 8, bar_y + 8)], fill="#FFFFFF")

        draw.text((x_start, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw, duration, font_small)
        draw.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        canvas.save(f"cache/{videoid}_{user_id}.png")
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
            title = result.get("title", "Unsupported Title")
            duration = result.get("duration", "Unknown")
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        try:
            owner_user = await app.get_users(OWNER_ID)
            wxy = await app.download_media(
                owner_user.photo.big_file_id,
                file_name=f"owner_{OWNER_ID}.jpg",
            )
        except Exception:
            wxy = await app.download_media(
                (await app.get_users(BOT_ID)).photo.big_file_id,
                file_name=f"{BOT_ID}.jpg",
            )

        try:
            req_user = await app.get_users(user_id)
            user_tag = f"@{req_user.username}" if req_user.username else req_user.first_name
        except:
            user_tag = "User"

        resample = getattr(Image.Resampling, "LANCZOS", Image.ANTIALIAS)

        canvas = Image.new("RGBA", (1280, 720), (12, 12, 16, 255))

        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        yt_resized = changeImageSize(600, 720, youtube)
        yt_crop = yt_resized.crop((0, 0, min(600, yt_resized.width), 720))
        canvas.paste(yt_crop, (0, 0))

        draw = ImageDraw.Draw(canvas)
        draw.line([(600, 0), (600, 720)], fill="#FF9800", width=5)

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 120
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_circle = make_circular_crop(owner_sq)

        canvas.paste(owner_circle, (1110, 560), mask=owner_circle)
        draw.ellipse([(1108, 558), (1232, 682)], fill=None, outline="#FF9800", width=3)

        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 40)
            font_sub = ImageFont.truetype(font_path, 28)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        x_start = 650

        draw.text((x_start, 120), "● ADDED TO QUEUE", fill="#FF9800", font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=20)
        draw.text((x_start, 180), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Requested by: {user_tag}", max_chars=24)
        draw.text((x_start, 260), req_text, fill="#A0A0A0", font=font_sub)

        bar_y = 420
        bar_x2 = 1220

        draw.line([(x_start, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=6)
        progress_x = x_start + int((bar_x2 - x_start) * 0.40)
        draw.line([(x_start, bar_y)], progress_x, bar_y), fill="#FF9800", width=6)
        draw.ellipse([(progress_x - 8, bar_y - 8), (progress_x + 8, bar_y + 8)], fill="#FFFFFF")

        draw.text((x_start, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw, duration, font_small)
        draw.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        canvas.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
