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


def make_rounded_crop(img, radius=25):
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
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

        # 1. إنشاء خلفية سوداء بالكامل (Deep Black)
        background = Image.new("RGBA", (1280, 720), (0, 0, 0, 255))

        # 2. إنشاء كارت أسود داخلي (Dark Card)
        card_w, card_h = 1080, 480
        card = Image.new("RGBA", (card_w, card_h), (10, 10, 10, 255))
        card_draw = ImageDraw.Draw(card)
        card_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=25, fill=(10, 10, 10, 255))

        # 3. قص وصورة المطور
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 360
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_rounded = make_rounded_crop(owner_sq, radius=20)

        card.paste(owner_rounded, (60, 60), mask=owner_rounded)

        # 4. تحميل الخط (تأكد من استبداله بملف يدعم العربي)
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 36)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(card)
        x_text = 460
        neon_color = "#00FFFF" # لون نيون أزرق سماوي

        draw_g.text((x_text, 80), "NOW PLAYING", fill="#E0E0E0", font=font_small)

        # عنوان الأغنية (يدعم العربي)
        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 130), formatted_title, fill=neon_color, font=font_title)

        # Requested by
        req_text = fix_arabic_text(f"Requested by {user_tag}", max_chars=30)
        draw_g.text((x_text, 205), req_text, fill="#CCCCCC", font=font_sub)

        # 5. شريط التقدم النيون
        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(50, 50, 50, 255), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.4)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill=neon_color, width=6)
        
        # تأثير توهج خفيف للكرة النيون
        draw_g.ellipse([(progress_x - 12, bar_y - 12), (progress_x + 12, bar_y + 12)], fill=(0, 255, 255, 50))
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill=neon_color)

        draw_g.text((bar_x1, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

        background.paste(card, (100, 120), mask=card)

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

        background = Image.new("RGBA", (1280, 720), (0, 0, 0, 255))

        card_w, card_h = 1080, 480
        card = Image.new("RGBA", (card_w, card_h), (10, 10, 10, 255))
        card_draw = ImageDraw.Draw(card)
        card_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=25, fill=(10, 10, 10, 255))

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 360
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_rounded = make_rounded_crop(owner_sq, radius=20)

        card.paste(owner_rounded, (60, 60), mask=owner_rounded)

        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 36)
            font_sub = ImageFont.truetype(font_path, 26)
            font_small = ImageFont.truetype(font_path, 22)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(card)
        x_text = 460
        neon_color_q = "#FF9800" # لون نيون برتقالي للقائمة

        draw_g.text((x_text, 80), "ADDED TO QUEUE", fill=neon_color_q, font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=24)
        draw_g.text((x_text, 130), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Requested by {user_tag}", max_chars=30)
        draw_g.text((x_text, 205), req_text, fill="#CCCCCC", font=font_sub)

        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(50, 50, 50, 255), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.4)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FFFFFF", width=6)
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill="#FFFFFF")

        draw_g.text((bar_x1, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

        background.paste(card, (100, 120), mask=card)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
