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


def draw_heart(draw, center, size, color):
    cx, cy = center
    pts = []
    for t in np.linspace(0, 2 * math.pi, 100):
        x = 16 * (math.sin(t) ** 3)
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        pts.append((cx + x * size / 16, cy + y * size / 16))
    draw.polygon(pts, fill=color)


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

        # 1. خلفية بخلفية الفيديو الخفيفة الضباب والواضحة
        canvas = Image.new("RGBA", (1280, 720), (12, 12, 16, 255))
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        
        # Blur خفيف (6) وسطوع أعلى (0.55) عشان الصورة تبان
        bg_yt = changeImageSize(1280, 720, youtube).filter(ImageFilter.GaussianBlur(6))
        bg_yt = ImageEnhance.Brightness(bg_yt).enhance(0.55)
        canvas.paste(bg_yt, (0, 0))

        # 2. الإطار الخارجي النيون المشطوف
        glow_layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        frame_pts = [
            (40, 70), (70, 40), (1210, 40), (1240, 70),
            (1240, 650), (1210, 680), (70, 680), (40, 650)
        ]
        glow_draw.polygon(frame_pts, outline="#FF1E27", width=4)
        canvas = Image.alpha_composite(canvas, glow_layer.filter(ImageFilter.GaussianBlur(8)))
        
        draw = ImageDraw.Draw(canvas)
        draw.polygon(frame_pts, outline="#FF3B45", width=2)

        # 3. إطار المسدس الكبير لصورة اليوتيوب
        hex_center = (280, 310)
        hex_radius = 200
        draw_hexagon(draw, hex_center, hex_radius + 8, outline="#FF1E27", width=4)
        draw_hexagon(draw, hex_center, hex_radius + 2, outline="#FFFFFF", width=2)

        sq_size = hex_radius * 2
        min_dim = min(youtube.width, youtube.height)
        crop_x = (youtube.width - min_dim) // 2
        crop_y = (youtube.height - min_dim) // 2
        yt_sq = youtube.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        yt_hex = make_hexagon_crop(yt_sq, hex_radius - 4)
        canvas.paste(yt_hex, (hex_center[0] - hex_radius, hex_center[1] - hex_radius), mask=yt_hex)

        # 4. النصوص والخطوط
        font_path = "ShahmMusic/Helpers/utils/font2.ttf"
        if not os.path.exists(font_path):
             font_path = ImageFont.load_default()

        try:
            font_title = ImageFont.truetype(font_path, 28)
            font_sub = ImageFont.truetype(font_path, 20)
            font_small = ImageFont.truetype(font_path, 15)
        except:
             font_title = font_sub = font_small = ImageFont.load_default()

        # Now Playing Header
        draw.text((540, 95), "—  NOW PLAYING  —", fill="#FF3B45", font=font_small)

        # Title Box
        draw.rounded_rectangle([(530, 125), (1190, 185)], radius=15, fill=(14, 14, 18, 220), outline="#2A2A38", width=2)
        formatted_title = fix_arabic_text(title, max_chars=28)
        draw.text((550, 137), formatted_title, fill="#FFFFFF", font=font_title)

        # Waveform Equalizer
        eq_x = 530
        eq_y = 235
        np.random.seed(len(title))
        for i in range(48):
            h = np.random.randint(6, 32)
            bar_color = "#FF3B45" if i < 28 else "#666677"
            draw.line([(eq_x + (i * 13), eq_y - h), (eq_x + (i * 13), eq_y + h)], fill=bar_color, width=3)

        # كارت المطور السُفلي + أيقونة القلب
        draw.rounded_rectangle([(530, 275), (1190, 405)], radius=18, fill=(10, 10, 14, 230), outline="#FF1E27", width=2)
        
        owner_img = Image.open(wxy).convert("RGBA")
        dev_sq = 90
        min_dev = min(owner_img.width, owner_img.height)
        dev_crop_x = (owner_img.width - min_dev) // 2
        dev_crop_y = (owner_img.height - min_dev) // 2
        owner_sq = owner_img.crop((dev_crop_x, dev_crop_y, dev_crop_x + min_dev, dev_crop_y + min_dev)).resize((dev_sq, dev_sq), resample)
        owner_circle = make_circular_crop(owner_sq)

        canvas.paste(owner_circle, (550, 295), mask=owner_circle)
        draw.ellipse([(548, 293), (642, 387)], fill=None, outline="#FF3B45", width=2)

        draw.text((660, 305), "BOT DEVELOPER", fill="#AAAAAB", font=font_small)
        req_text = fix_arabic_text(f"Order: {user_tag}", max_chars=22)
        draw.text((660, 335), req_text, fill="#FFFFFF", font=font_sub)

        # رسم قلب المطور على اليمين inside developer card
        draw_heart(draw, (1140, 340), 1.2, "#FF1E27")

        # 5. شريط التشغيل المضيء (Spotify Progress Bar Area)
        bar_y = 460
        bar_x1 = 90
        bar_x2 = 1190

        draw.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill="#333344", width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.42)
        draw.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FF1E27", width=6)
        draw.ellipse([(progress_x - 8, bar_y - 8), (progress_x + 8, bar_y + 8)], fill="#FFFFFF", outline="#FF1E27", width=2)

        draw.text((bar_x1, bar_y + 12), "0:01", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw, duration, font_small)
        draw.text((bar_x2 - dur_w, bar_y + 12), duration, fill="#FFFFFF", font=font_small)

        # 6. شريط أزرار Spotify والتحكم السفلي الكامل
        draw.rounded_rectangle([(80, 520), (1200, 620)], radius=20, fill=(8, 8, 12, 230), outline="#2A2A38", width=1)

        # شعار Spotify جهة اليسار
        draw.ellipse([(110, 548), (145, 583)], fill="#FF1E27")
        draw.arc([(117, 555), (138, 570)], start=200, end=340, fill="#FFFFFF", width=2)
        draw.arc([(119, 561), (136, 574)], start=200, end=340, fill="#FFFFFF", width=2)
        draw.text((155, 550), "Listen on", fill="#AAAAAB", font=font_small)
        draw.text((155, 565), "Spotify", fill="#FFFFFF", font=font_sub)

        # أزرار التشغيل المركزية
        draw.text((380, 557), "🔀", fill="#FF1E27", font=font_sub)
        
        draw.polygon([(480, 560), (480, 580), (465, 570)], fill="#FFFFFF")
        draw.rectangle([(462, 560), (465, 580)], fill="#FFFFFF")

        draw_hexagon(draw, (640, 570), 34, fill="#121218", outline="#FF1E27", width=3)
        draw.rectangle([(631, 557), (636, 583)], fill="#FFFFFF")
        draw.rectangle([(644, 557), (649, 583)], fill="#FFFFFF")

        draw.polygon([(800, 560), (800, 580), (815, 570)], fill="#FFFFFF")
        draw.rectangle([(815, 560), (818, 580)], fill="#FFFFFF")

        draw.text((900, 557), "🔁", fill="#FF1E27", font=font_sub)

        # Volume Slider جهة اليمين
        draw.text((1020, 558), "🔊", fill="#FFFFFF", font=font_small)
        draw.line([(1050, 570), (1160, 570)], fill="#444455", width=4)
        draw.line([(1050, 570), (1120, 570)], fill="#FF1E27", width=4)
        draw.ellipse([(1116, 566), (1124, 574)], fill="#FFFFFF")

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
