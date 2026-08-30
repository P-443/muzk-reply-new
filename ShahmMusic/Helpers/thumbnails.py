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
    """قص الصورة في شكل دائرة كاملة أنيقة"""
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

        # 1. خلفية الصورة مع تضبيب سينمائي داكن
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        background = changeImageSize(1280, 720, youtube)
        background = background.filter(ImageFilter.GaussianBlur(15))
        background = ImageEnhance.Brightness(background).enhance(0.35)

        # 2. الكارت الرئيسي بتصميم داكن مع حواف مضيئة
        card_w, card_h = 1080, 480
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=40, fill=(15, 15, 25, 180), outline=(138, 43, 226, 120), width=3)

        # 3. قص صورة المطور في شكل دائرة مع حلقة نيون
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 340
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_circle = make_circular_crop(owner_sq)

        # رسم إطار دائري نيون خلف الصورة
        glass_draw.ellipse([(60, 70), (410, 420)], fill=None, outline="#8A2BE2", width=4)
        glass.paste(owner_circle, (65, 75), mask=owner_circle)

        # 4. تحميل الخطوط
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 36)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)
        x_text = 450

        # عنوان البث
        draw_g.text((x_text, 80), "● PLAYING NOW", fill="#00FFFF", font=font_small)

        # اسم الأغنية (يدعم العربي)
        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 130), formatted_title, fill="#FFFFFF", font=font_title)

        # Requested by
        req_text = fix_arabic_text(f"Requested by {user_tag}", max_chars=28)
        draw_g.text((x_text, 205), req_text, fill="#B0B0C0", font=font_sub)

        # 5. شريط التقدم بنمط مستقبلي
        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=8)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.45)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#8A2BE2", width=8)
        draw_g.ellipse([(progress_x - 12, bar_y - 12), (progress_x + 12, bar_y + 12)], fill="#00FFFF")

        draw_g.text((bar_x1, bar_y + 25), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 25), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (100, 120), mask=glass)

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

        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        background = changeImageSize(1280, 720, youtube)
        background = background.filter(ImageFilter.GaussianBlur(15))
        background = ImageEnhance.Brightness(background).enhance(0.35)

        card_w, card_h = 1080, 480
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=40, fill=(15, 15, 25, 180), outline=(255, 152, 0, 120), width=3)

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 340
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_circle = make_circular_crop(owner_sq)

        glass_draw.ellipse([(60, 70), (410, 420)], fill=None, outline="#FF9800", width=4)
        glass.paste(owner_circle, (65, 75), mask=owner_circle)

        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 36)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)
        x_text = 450

        draw_g.text((x_text, 80), "● ADDED TO QUEUE", fill="#FF9800", font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 130), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Requested by {user_tag}", max_chars=28)
        draw_g.text((x_text, 205), req_text, fill="#B0B0C0", font=font_sub)

        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=8)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.45)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FF9800", width=8)
        draw_g.ellipse([(progress_x - 12, bar_y - 12), (progress_x + 12, bar_y + 12)], fill="#FFFFFF")

        draw_g.text((bar_x1, bar_y + 25), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 25), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (100, 120), mask=glass)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
