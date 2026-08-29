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


def fix_arabic_text(text):
    """معالجة وتعديل اتجاه النص العربي"""
    if not text:
        return ""
    try:
        # إعادة تشكيل الحروف العربية وربطها
        reshaped_text = arabic_reshaper.reshape(text)
        # ضبط الاتجاه من اليمين لليسار
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
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


def load_arabic_font(size):
    """تحميل خط يدعم العربية مع حلول بديلة في حال عدم وجود الخط الأساسي"""
    font_paths = [
        "ShahmMusic/Helpers/utils/font2.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # متوفر غالباً في السيرفرات واللينكس
        "arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


async def gen_thumb(videoid, user_id):
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"
    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
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

        # جلب صورة مالك البوت (المطور)
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

        # 1. إظهار معالم صورة اليوتيوب في الخلفية (تخفيف التضبيب)
        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        background = changeImageSize(1280, 720, youtube)
        background = background.filter(ImageFilter.GaussianBlur(6))
        background = ImageEnhance.Brightness(background).enhance(0.55)

        # 2. إنشاء الكارت الزجاجي
        card_w, card_h = 1080, 480
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=35, fill=(0, 0, 0, 110), outline=(255, 255, 255, 90), width=2)

        # 3. قص وتجهيز صورة المطور
        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 360
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_rounded = make_rounded_crop(owner_sq, radius=30)

        glass.paste(owner_rounded, (60, 60), mask=owner_rounded)

        # 4. تحميل الخطوط المقاومة لمشاكل العربي
        font_title = load_arabic_font(36)
        font_sub = load_arabic_font(26)
        font_small = load_arabic_font(22)

        draw_g = ImageDraw.Draw(glass)
        x_text = 460

        draw_g.ellipse([(x_text, 88), (x_text + 12, 100)], fill="#FFFFFF")
        draw_g.text((x_text + 25, 80), "NOW PLAYING", fill="#E0E0E0", font=font_small)

        # معالجة العنوان العربي
        short_title = title[:24] + "..." if len(title) > 24 else title
        formatted_title = fix_arabic_text(short_title)
        draw_g.text((x_text, 130), formatted_title, fill="#FFFFFF", font=font_title)

        # Requested by
        req_text = fix_arabic_text(f"Requested by {user_tag}")
        draw_g.text((x_text, 205), req_text, fill="#CCCCCC", font=font_sub)

        # 5. شريط التقديم
        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 100), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.4)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FFFFFF", width=6)
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill="#FFFFFF")

        draw_g.text((bar_x1, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

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
            try:
                title = result["title"]
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
        background = background.filter(ImageFilter.GaussianBlur(6))
        background = ImageEnhance.Brightness(background).enhance(0.55)

        card_w, card_h = 1080, 480
        glass = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        glass_draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=35, fill=(0, 0, 0, 110), outline=(255, 255, 255, 90), width=2)

        owner_img = Image.open(wxy).convert("RGBA")
        sq_size = 360
        min_dim = min(owner_img.width, owner_img.height)
        crop_x = (owner_img.width - min_dim) // 2
        crop_y = (owner_img.height - min_dim) // 2
        owner_sq = owner_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim)).resize((sq_size, sq_size), resample)
        owner_rounded = make_rounded_crop(owner_sq, radius=30)

        glass.paste(owner_rounded, (60, 60), mask=owner_rounded)

        font_title = load_arabic_font(36)
        font_sub = load_arabic_font(26)
        font_small = load_arabic_font(22)

        draw_g = ImageDraw.Draw(glass)
        x_text = 460

        draw_g.ellipse([(x_text, 88), (x_text + 12, 100)], fill="#FF9800")
        draw_g.text((x_text + 25, 80), "ADDED TO QUEUE", fill="#FF9800", font=font_small)

        short_title = title[:24] + "..." if len(title) > 24 else title
        formatted_title = fix_arabic_text(short_title)
        draw_g.text((x_text, 130), formatted_title, fill="#FFFFFF", font=font_title)

        req_text = fix_arabic_text(f"Requested by {user_tag}")
        draw_g.text((x_text, 205), req_text, fill="#CCCCCC", font=font_sub)

        bar_x1 = x_text
        bar_y = 310
        bar_x2 = card_w - 60

        draw_g.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(255, 255, 255, 100), width=6)
        progress_x = bar_x1 + int((bar_x2 - bar_x1) * 0.4)
        draw_g.line([(bar_x1, bar_y), (progress_x, bar_y)], fill="#FFFFFF", width=6)
        draw_g.ellipse([(progress_x - 10, bar_y - 10), (progress_x + 10, bar_y + 10)], fill="#FFFFFF")

        draw_g.text((bar_x1, bar_y + 20), "0:00", fill="#FFFFFF", font=font_small)
        dur_w, _ = get_text_size(draw_g, duration, font_small)
        draw_g.text((bar_x2 - dur_w, bar_y + 20), duration, fill="#FFFFFF", font=font_small)

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
