import os
import re
import math
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


def draw_hexagon(draw, center, radius, fill=None, outline=None, width=1):
    cx, cy = center
    points = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        px = cx + radius * math.cos(angle_rad)
        py = cy + radius * math.sin(angle_rad)
        points.append((px, py))
    if fill:
        draw.polygon(points, fill=fill)
    if outline:
        points.append(points[0])
        draw.line(points, fill=outline, width=width)
    return points


def make_hexagon_crop(img, radius):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw_hexagon(draw, (w // 2, h // 2), radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result


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

        # 1. إنشاء خلفية سايبر داكنة جداً مع توهج أحمر
        canvas = Image.new("RGBA", (1280, 720), (8, 8, 12, 255))
        
        # صورة اليوتيوب خلفية مع Blur خفيف لإعطاء جو معتم
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        bg_yt = changeImageSize(1280, 720, youtube).filter(ImageFilter.GaussianBlur(15))
        bg_yt = ImageEnhance.Brightness(bg_yt).enhance(0.25)
        canvas.paste(bg_yt, (0, 0))

        # 2. رسم الإطار الخارجي والحدود المضيئة (Cyber Frame)
        glow_layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        # الحدود الخارجية المقطوعة الزوايا
        frame_pts = [
            (50, 80), (80, 50), (1200, 50), (1230, 80),
            (1230, 640), (1200, 670), (80, 670), (50, 640)
        ]
        glow_draw.polygon(frame_pts, outline="#FF1E27", width=4)
        
        # طبقة توهج نيون عالية الجودة
        glow_blur = glow_layer.filter(ImageFilter.GaussianBlur(8))
        canvas = Image.alpha_composite(canvas, glow_blur)
        
        draw = ImageDraw.Draw(canvas)
        draw.polygon(frame_pts, outline="#FF3B45", width=2)

        # 3. إطار المسدس الكبير (Left Hexagon) لصورة الفيديو
        hex_center = (290, 310)
        hex_radius = 210

        # رسم توهج أحمر للمسدس
        draw_hexagon(draw, hex_center, hex_radius + 8, outline="#FF1E27", width=5)
        draw_hexagon(draw, hex_center, hex_radius + 2, outline="#FFFFFF", width=2)

        # قص وتثبيت صورة اليوتيوب داخل المسدس
        sq_size = hex_radius * 2
        min_dim = min(youtube.width, youtube.height)
        crop_x = (youtube.width - min_dim) // 2
        crop_y = (youtube.height - min_dim) // 2
        yt_sq = youtube.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        yt_hex = make_hexagon_crop(yt_sq, hex_radius - 5)
        
        canvas.paste(yt_hex, (hex_center[0] - hex_radius, hex_center[1] - hex_radius), mask=yt_hex)

        # 4. المكونات اليمنى (Now Playing + Waveform + Owner Card)
        # عنوان المقطع
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 30)
            font_sub = ImageFont.truetype(font_path, 20)
            font_small = ImageFont.truetype(font_path, 16)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        draw.text((560, 110), "—  NOW PLAYING  —", fill="#FF3B45", font=font_small)

        # صندوق العنوان العائم
        draw.rounded_rectangle([(550, 140), (1170, 200)], radius=15, fill=(18, 18, 24, 200), outline="#333344", width=2)
        formatted_title = fix_arabic_text(title, max_chars=28)
        draw.text((570, 152), formatted_title, fill="#FFFFFF", font=font_title)

        # الموجات الصوتية (Equalizer)
        eq_x = 550
        eq_y = 250
        np.random.seed(len(title))  # توحيد شكل الموجة حسب اسم الأغنية
        for i in range(45):
            h = np.random.randint(8, 35)
            bar_color = "#FF3B45" if i < 25 else "#555566"
            draw.line([(eq_x + (i * 13), eq_y - h), (eq_x + (i * 13), eq_y + h)], fill=bar_color, width=4)

        # كارت المطور المصغر
        draw.rounded_rectangle([(550, 290), (1170, 420)], radius=20, fill=(15, 15, 20, 220), outline="#FF1E27", width=2)
        
        # صورة المطور الدائرية
        owner_img = Image.open(wxy).convert("RGBA")
        dev_sq = 90
        min_dev = min(owner_img.width, owner_img.height)
        dev_crop_x = (owner_img.width - min_dev) // 2
        dev_crop_y = (owner_img.height - min_dev) // 2
        owner_sq = owner_img.crop((dev_crop_x, dev_crop_y, dev_crop_x + min_dev, dev_crop_y + min_dev)).resize((dev_sq, dev_sq), resample)
        owner_circle = make_circular_crop(owner_sq)

        canvas.paste(owner_circle, (570, 310), mask=owner_circle)
        draw.ellipse([(568, 308), (662, 402)], fill=None, outline="#FF3B45", width=2)

        draw.text((680, 318), "BOT DEVELOPER", fill="#888899", font=font_small)
        req_text = fix_arabic_text(f"Order: {user_tag}", max_chars=22)
        draw.text((680, 350), req_text, fill="#FFFFFF", font=font_sub)

        # 5. شريط التقديم والأزرار السفلي (Player Control Bar)
        bar_y = 480
        draw.line([(100, bar_y), (1180, bar_y)], fill="#333344", width=6)
        progress_x = 100 + int((1180 - 100) * 0.45)
        draw.line([(100, bar_y), (progress_x, bar_y)], fill="#FF3B45", width=6)
        draw.ellipse([(progress_x - 8, bar_y - 8), (progress_x + 8, bar_y + 8)], fill="#FFFFFF", outline="#FF3B45", width=2)

        draw.text((100, bar_y + 15), "0:01", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw, duration, font_small)
        draw.text((1180 - dur_w, bar_y + 15), duration, fill="#FFFFFF", font=font_small)

        # زر التشغيل/الإيقاف السداسي المركزي في الأسفل
        draw_hexagon(draw, (640, 570), 38, fill="#121218", outline="#FF3B45", width=3)
        # خطين pause باللون الأبيض
        draw.rectangle([(630, 555), (636, 585)], fill="#FFFFFF")
        draw.rectangle([(644, 555), (650, 585)], fill="#FFFFFF")

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
    res = await gen_thumb(videoid, user_id)
    if res != FAILED:
        os.rename(res, f"cache/que{videoid}_{user_id}.png")
        return f"cache/que{videoid}_{user_id}.png"
    return FAILED
