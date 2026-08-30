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


def make_octagon_crop(img):
    """قص الصورة في شكل ثماني الأضلاع فاخر (VIP Octagon)"""
    w, h = img.size
    offset = int(w * 0.28)
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    points = [
        (offset, 0), (w - offset, 0),
        (w, offset), (w, h - offset),
        (w - offset, h), (offset, h),
        (0, h - offset), (0, offset)
    ]
    draw.polygon(points, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result, points


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

        # 1. خلفية الصورة مع ضباب شبه معدوم (Blur = 2) لوضوح كامل
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        background = changeImageSize(1280, 720, youtube)
        background = background.filter(ImageFilter.GaussianBlur(2))
        background = ImageEnhance.Brightness(background).enhance(0.55)

        # 2. بطاقة VIP رئيسية بتصميم فاخر وجوانب مشطوفة
        card_w, card_h = 1100, 500
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        
        # خلفية سوداء عميقة شفافة بإطارين نيون زمرادي مضيء
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=35, fill=(8, 10, 14, 215), outline="#00FF88", width=3)
        glass_draw.rounded_rectangle([(8, 8), (card_w - 8, card_h - 8)], radius=28, fill=None, outline=(255, 255, 255, 30), width=1)

        # 3. قص صورة المطور في شكل ثماني الأضلاع فاخر جداً
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 320
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_oct, oct_points = make_octagon_crop(owner_sq)

        # إطار ثماني الأضلاع المضيء
        ox, oy = 70, 90
        shifted_points = [(p[0] + ox, p[1] + oy) for p in oct_points]
        glass_draw.polygon(shifted_points, outline="#00FF88", width=4)
        glass.paste(owner_oct, (ox, oy), mask=owner_oct)

        # 4. تحميل الخطوط
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 38)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)
        x_text = 440

        # شريط الحالة VIP
        draw_g.text((x_text, 90), "✦ VIP NOW PLAYING ✦", fill="#00FF88", font=font_small)

        # عنوان المقطع بالعربي
        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 140), formatted_title, fill="#FFFFFF", font=font_title)

        # اسم الطلب
        req_text = fix_arabic_text(f"Requested by: {user_tag}", max_chars=28)
        draw_g.text((x_text, 215), req_text, fill="#CCCCCC", font=font_sub)

        # 5. شريط التقديم الفاخر
        bar_x1 = x_text
        bar_y = 320
        bar_x2 = card_w - 70

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.48)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#00FF88", width=6)
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill="#FFFFFF", outline="#00FF88", width=3)

        draw_g.text((bar_x1, bar_y + 22), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 22), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (90, 110), mask=glass)

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
        background = background.filter(ImageFilter.GaussianBlur(2))
        background = ImageEnhance.Brightness(background).enhance(0.55)

        card_w, card_h = 1100, 500
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=35, fill=(8, 10, 14, 215), outline="#FF9800", width=3)
        glass_draw.rounded_rectangle([(8, 8), (card_w - 8, card_h - 8)], radius=28, fill=None, outline=(255, 255, 255, 30), width=1)

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 320
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_oct, oct_points = make_octagon_crop(owner_sq)

        ox, oy = 70, 90
        shifted_points = [(p[0] + ox, p[1] + oy) for p in oct_points]
        glass_draw.polygon(shifted_points, outline="#FF9800", width=4)
        glass.paste(owner_oct, (ox, oy), mask=owner_oct)

        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 38)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)
        x_text = 440

        draw_g.text((x_text, 90), "✦ VIP ADDED TO QUEUE ✦", fill="#FF9800", font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 140), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Requested by: {user_tag}", max_chars=28)
        draw_g.text((x_text, 215), req_text, fill="#CCCCCC", font=font_sub)

        bar_x1 = x_text
        bar_y = 320
        bar_x2 = card_w - 70

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 40), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.48)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FF9800", width=6)
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill="#FFFFFF", outline="#FF9800", width=3)

        draw_g.text((bar_x1, bar_y + 22), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 22), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (90, 110), mask=glass)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
