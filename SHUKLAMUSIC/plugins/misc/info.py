import asyncio, os, time, aiohttp
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from asyncio import sleep
from SHUKLAMUSIC import app
from pyrogram import filters, enums
from pyrogram.types import *
from typing import Union, Optional
import random

# ================================
# Random Photo
# ================================

random_photo = [
    "https://files.catbox.moe/dcln36.jpg",
]

# ================================
# Image Helpers
# ================================

get_font = lambda font_size, font_path: ImageFont.truetype(font_path, font_size)

async def get_userinfo_img(
    bg_path: str,
    font_path: str,
    user_id: Union[int, str],    
    profile_path: Optional[str] = None
):
    bg = Image.open(bg_path)

    if profile_path:
        img = Image.open(profile_path)
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.pieslice([(0, 0), img.size], 0, 360, fill=255)

        circular_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)
        resized = circular_img.resize((400, 400))
        bg.paste(resized, (440, 160), resized)

    img_draw = ImageDraw.Draw(bg)

    img_draw.text(
        (529, 627),
        text=str(user_id).upper(),
        font=get_font(46, "SHUKLAMUSIC/assets/hiroko.ttf"),
        fill=(255, 255, 255),
    )

    path = f"./userinfo_img_{user_id}.png"
    bg.save(path)
    return path


# ================================
# Default Info Text
# ================================

INFO_TEXT = """
<b>[ᯤ] USER INFORMATION [ᯤ]</b>

🍹 <b>User ID :</b> <code>{}</code>
💓 <b>First Name :</b> {}
💗 <b>Last Name :</b> {}
🍷 <b>Username :</b> <code>{}</code>
🍬 <b>Mention :</b> {}
🍁 <b>Status :</b> {}
🎫 <b>DC ID :</b> {}
🗨️ <b>Bio :</b> <code>{}</code>
"""


# ================================
# User Status
# ================================

async def userstatus(user_id):
    try:
        user = await app.get_users(user_id)
        x = user.status
        if x == enums.UserStatus.RECENTLY:
            return "Recently"
        elif x == enums.UserStatus.LAST_WEEK:
            return "Last week"
        elif x == enums.UserStatus.LONG_AGO:
            return "Long time ago"
        elif x == enums.UserStatus.OFFLINE:
            return "Offline"
        elif x == enums.UserStatus.ONLINE:
            return "Online"
    except:
        return "Unknown"


# ================================
# SET INFO MESSAGE COMMAND
# ================================

@app.on_message(filters.command(["setinfo"]) & filters.user(7789325573))
async def set_info_msg(client, message):

    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(
            "❌ <b>Usage:</b>\n"
            "<code>/setinfo [Your HTML Message]</code>\n\n"
            "<b>Variables:</b>\n"
            "<code>{id}</code>\n"
            "<code>{first_name}</code>\n"
            "<code>{last_name}</code>\n"
            "<code>{username}</code>\n"
            "<code>{mention}</code>\n"
            "<code>{status}</code>\n"
            "<code>{dc_id}</code>\n"
            "<code>{bio}</code>"
        )
        return

    try:
        if message.reply_to_message:
            new_msg = message.reply_to_message.text.html or message.reply_to_message.caption.html
        else:
            new_msg = message.text.html.split(None, 1)[1]
    except:
        return await message.reply_text("❌ Text extract nahi ho paya.")

    await welcome_db.update_one(
        {"_id": "info_message"},
        {"$set": {"message": new_msg}},
        upsert=True
    )

    await message.reply_text("✅ <b>INFO message set successfully!</b>")


# ================================
# Get Custom Info Caption
# ================================

async def get_info_caption(default_text, user_info, user, status):

    data = await welcome_db.find_one({"_id": "info_message"})

    if data and "message" in data:
        text = data["message"]

        text = text.replace("{id}", str(user_info.id))
        text = text.replace("{first_name}", user_info.first_name or "No Name")
        text = text.replace("{last_name}", user_info.last_name or "No Last Name")
        text = text.replace("{username}", f"@{user_info.username}" if user_info.username else "No Username")
        text = text.replace("{mention}", user.mention)
        text = text.replace("{status}", status)
        text = text.replace("{dc_id}", str(user.dc_id))
        text = text.replace("{bio}", user_info.bio or "No bio set")

        return text

    return default_text


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

        id = user_info.id
        dc_id = user.dc_id
        first_name = user_info.first_name or "No Name"
        last_name = user_info.last_name or "No Last Name"
        username = user_info.username or "No Username"
        mention = user.mention
        bio = user_info.bio or "No bio set"

        if user.photo:
            photo = await app.download_media(user.photo.big_file_id)
            welcome_photo = await get_userinfo_img(
                bg_path="SHUKLAMUSIC/assets/userinfox.png",
                font_path="SHUKLAMUSIC/assets/hiroko.ttf",
                user_id=user.id,
                profile_path=photo,
            )
        else:
            welcome_photo = random.choice(random_photo)

        caption = await get_info_caption(
            INFO_TEXT.format(
                id, first_name, last_name, username, mention, status, dc_id, bio
            ),
            user_info,
            user,
            status
        )

        await app.send_photo(
            message.chat.id,
            photo=welcome_photo,
            caption=caption,
            reply_to_message_id=message.id
        )

    except Exception as e:
        await message.reply_text(str(e))
