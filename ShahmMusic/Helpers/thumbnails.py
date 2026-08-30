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


def make_diamond_crop(img):
    """قص الصورة في شكل ماسة / سداسي عصري"""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # رسم ماسة احترافية
    points = [(w // 2, 0), (w, h // 2), (w // 2, h), (0, h // 2)]
    draw.polygon(points, fill=255)
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

        # 1. خلفية اليوتيوب واضحة جداً (ضباب 3 فقط)
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        background = changeImageSize(1280, 720, youtube)
        background = background.filter(ImageFilter.GaussianBlur(3))
        background = ImageEnhance.Brightness(background).enhance(0.75)

        # 2. كارت هيدر فخم وسفلي شفاف مع إضافة خط نيون
        card_w, card_h = 1120, 520
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        
        # خلفية سوداء ناعمة مع إطار نيون فيروزي
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=30, fill=(12, 16, 28, 190), outline="#00F2FE", width=3)

        # 3. إدراج صورة اليوتيوب الأصلية داخل كارت أنيق على اليسار
        yt_card = changeImageSize(360, 240, youtube)
        yt_crop = Image.new("RGBA", (360, 240), (0, 0, 0, 0))
        yt_draw = ImageDraw.Draw(yt_crop)
        yt_draw.rounded_rectangle([(0, 0), (360, 240)], radius=20, fill=(255, 255, 255, 255))
        yt_crop.paste(yt_card, (0, 0))
        glass.paste(yt_crop, (50, 50))

        # 4. صورة المطور على شكل ماسة متألقة برابط نيون
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 180
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_diamond = make_diamond_crop(owner_sq)

        # إطار الماسة
        glass_draw.polygon([(card_w - 140, 40), (card_w - 40, 140), (card_w - 140, 240), (card_w - 240, 140)], outline="#4FACFE", width=4)
        glass.paste(owner_diamond, (card_w - 230, 50), mask=owner_diamond)

        # 5. تحميل الخطوط
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 34)
            font_sub = ImageFont.truetype(font_path, 24)
            font_small = ImageFont.truetype(font_path, 20)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)
        
        # النصوص والمعلومات
        draw_g.text((440, 60), "⚡ STREAMING NOW", fill="#00F2FE", font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=22)
        draw_g.text((440, 105), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Order by: {user_tag}", max_chars=25)
        draw_g.text((440, 175), req_text, fill="#A0AABF", font=font_sub)

        # 6. شريط التقدم النيون العريض
        bar_x1 = 50
        bar_y = 350
        bar_x2 = card_w - 50

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 30), width=10)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.50)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#00F2FE", width=10)
        draw_g.ellipse([(progress_x - 12, bar_y - 12), (progress_x + 12, bar_y + 12)], fill="#FFFFFF", outline="#00F2FE", width=3)

        draw_g.text((bar_x1, bar_y + 25), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 25), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (80, 100), mask=glass)

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
        background = background.filter(ImageFilter.GaussianBlur(3))
        background = ImageEnhance.Brightness(background).enhance(0.75)

        card_w, card_h = 1120, 520
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=30, fill=(12, 16, 28, 190), outline="#FF9800", width=3)

        yt_card = changeImageSize(360, 240, youtube)
        yt_crop = Image.new("RGBA", (360, 240), (0, 0, 0, 0))
        yt_draw = ImageDraw.Draw(yt_crop)
        yt_draw.rounded_rectangle([(0, 0), (360, 240)], radius=20, fill=(255, 255, 255, 255))
        yt_crop.paste(yt_card, (0, 0))
        glass.paste(yt_crop, (50, 50))

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 180
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_diamond = make_diamond_crop(owner_sq)

        glass_draw.polygon([(card_w - 140, 40), (card_w - 40, 140), (card_w - 140, 240), (card_w - 240, 140)], outline="#FF9800", width=4)
        glass.paste(owner_diamond, (card_w - 230, 50), mask=owner_diamond)

        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 34)
            font_sub = ImageFont.truetype(font_path, 24)
            font_small = ImageFont.truetype(font_path, 20)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw_g = ImageDraw.Draw(glass)

        draw_g.text((440, 60), "⏳ ADDED TO QUEUE", fill="#FF9800", font=font_small)

        formatted_title = fix_arabic_text(title, max_chars=22)
        draw_g.text((440, 105), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Order by: {user_tag}", max_chars=25)
        draw_g.text((440, 175), req_text, fill="#A0AABF", font=font_sub)

        bar_x1 = 50
        bar_y = 350
        bar_x2 = card_w - 50

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 30), width=10)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.50)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FF9800", width=10)
        draw_g.ellipse([(progress_x - 12, bar_y - 12), (progress_x + 12, bar_y + 12)], fill="#FFFFFF", outline="#FF9800", width=3)

        draw_g.text((bar_x1, bar_y + 25), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 25), duration, fill="#FFFFFF", font=font_small)

        background.paste(glass, (80, 100), mask=glass)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    except Exception as e:
        LOGGER.error(e)
        return FAILED
