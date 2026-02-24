import asyncio, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Union, Optional

from SHUKLAMUSIC import app
from pyrogram import filters, enums
from pyrogram.types import *
from pyrogram.enums import ParseMode
from motor.motor_asyncio import AsyncIOMotorClient
import config


# ================================
# Mongo Setup
# ================================

mongo_client = AsyncIOMotorClient(config.MONGO_DB_URI)
db = mongo_client["MOON_DB"]
welcome_db = db["INFO_SETTINGS"]


# ================================
# Random Photo
# ================================

random_photo = [
    "https://files.catbox.moe/dcln36.jpg",
]


# ================================
# Image Generator
# ================================

async def get_userinfo_img(
    bg_path: str,
    font_path: str,
    user_id: Union[int, str],
    profile_path: Optional[str] = None,
):
    bg = Image.open(bg_path)

    if profile_path and os.path.exists(profile_path):
        img = Image.open(profile_path)

        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)

        img.putalpha(mask)
        img = img.resize((400, 400))

        bg.paste(img, (440, 160), img)

    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(font_path, 46)
    draw.text((529, 627), str(user_id), font=font, fill=(255, 255, 255))

    output = f"./userinfo_{user_id}.png"
    bg.save(output)
    return output


# ================================
# Default Caption
# ================================

DEFAULT_INFO = """
<b>🌸 USER INFORMATION 🌸</b>

🆔 <b>ID :</b> <code>{id}</code>
👤 <b>First Name :</b> {first_name}
👥 <b>Last Name :</b> {last_name}
🔗 <b>Username :</b> <code>{username}</code>
💌 <b>Mention :</b> {mention}
📡 <b>Status :</b> {status}
📦 <b>DC ID :</b> {dc_id}
📝 <b>Bio :</b> <code>{bio}</code>
"""


# ================================
# User Status
# ================================

async def userstatus(user_id):
    try:
        user = await app.get_users(user_id)
        status = user.status

        if status == enums.UserStatus.ONLINE:
            return "Online"
        elif status == enums.UserStatus.OFFLINE:
            return "Offline"
        elif status == enums.UserStatus.RECENTLY:
            return "Recently"
        elif status == enums.UserStatus.LAST_WEEK:
            return "Last Week"
        else:
            return "Long Time Ago"

    except:
        return "Unknown"


# ================================
# SET INFO COMMAND (Premium Emoji Supported)
# ================================

@app.on_message(filters.command(["setinfo"]) & filters.user(7789325573))
async def set_info_msg(client, message):

    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(
            "❌ Usage:\n/setinfo Your HTML Text\n\n"
            "Variables:\n"
            "{id}\n{first_name}\n{last_name}\n{username}\n"
            "{mention}\n{status}\n{dc_id}\n{bio}"
        )

    try:
        if message.reply_to_message:
            new_text = (
                message.reply_to_message.text.html
                if message.reply_to_message.text
                else message.reply_to_message.caption.html
            )
        else:
            new_text = message.text.html.split(None, 1)[1]

    except Exception:
        return await message.reply_text("❌ Text extract failed.")

    await welcome_db.update_one(
        {"_id": "info_caption"},
        {"$set": {"message": new_text}},
        upsert=True,
    )

    await message.reply_text("✅ Custom INFO message saved!")


# ================================
# Get Caption
# ================================

async def build_caption(user_info, user, status):

    data = await welcome_db.find_one({"_id": "info_caption"})

    if data and "message" in data:
        text = data["message"]
    else:
        text = DEFAULT_INFO

    return text.format(
        id=user_info.id,
        first_name=user_info.first_name or "No Name",
        last_name=user_info.last_name or "No Last Name",
        username=f"@{user_info.username}" if user_info.username else "No Username",
        mention=user.mention,
        status=status,
        dc_id=user.dc_id,
        bio=user_info.bio or "No Bio",
    )


# ================================
# INFO COMMAND
# ================================

@app.on_message(filters.command(["info", "userinfo"]))
async def userinfo(_, message):

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) == 2:
        user_id = message.command[1]
    else:
        user_id = message.from_user.id

    try:
        user_info = await app.get_chat(user_id)
        user = await app.get_users(user_id)
        status = await userstatus(user.id)

        caption = await build_caption(user_info, user, status)

        if user.photo:
            photo_path = await app.download_media(user.photo.big_file_id)

            image_path = await get_userinfo_img(
                "SHUKLAMUSIC/assets/userinfox.png",
                "SHUKLAMUSIC/assets/hiroko.ttf",
                user.id,
                photo_path,
            )
        else:
            image_path = random.choice(random_photo)

        await message.reply_photo(
            photo=image_path,
            caption=caption,
            parse_mode=ParseMode.HTML
        )

        if isinstance(image_path, str) and image_path.startswith("./userinfo_"):
            os.remove(image_path)

    except Exception as e:
        await message.reply_text(f"Error: {e}")
