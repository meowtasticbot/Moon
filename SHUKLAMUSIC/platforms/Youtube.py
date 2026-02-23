import asyncio
import os
import re
from typing import Union, Tuple, List

import aiohttp
import yt_dlp

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from SHUKLAMUSIC.utils.formatters import time_to_seconds
from SHUKLAMUSIC import LOGGER

try:
    from py_yt import VideosSearch, Playlist
except ImportError:
    from youtubesearchpython.__future__ import VideosSearch
    Playlist = None


API_URL = "https://shrutibots.site"
DOWNLOAD_DIR = "downloads"


# ------------------------------------------------
# BASIC HELPERS
# ------------------------------------------------

def get_video_id(link: str) -> Union[str, None]:
    if not link:
        return None
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    return link if len(link) >= 3 else None


def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ------------------------------------------------
# API BASED DOWNLOADS
# ------------------------------------------------

async def download_song(link: str) -> Union[str, None]:
    video_id = get_video_id(link)
    if not video_id:
        return None

    ensure_download_dir()
    file_path = f"{DOWNLOAD_DIR}/{video_id}.mp3"

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": "audio"}
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=7),
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                token = data.get("download_token")
                if not token:
                    return None

            stream_url = f"{API_URL}/stream/{video_id}?type=audio&token={token}"
            async with session.get(
                stream_url,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as fr:
                if fr.status == 302:
                    redirect = fr.headers.get("Location")
                    if not redirect:
                        return None
                    async with session.get(redirect) as rr:
                        if rr.status != 200:
                            return None
                        with open(file_path, "wb") as f:
                            async for chunk in rr.content.iter_chunked(16384):
                                f.write(chunk)

                elif fr.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in fr.content.iter_chunked(16384):
                            f.write(chunk)
                else:
                    return None

        return file_path if os.path.getsize(file_path) > 0 else None

    except Exception as e:
        LOGGER.error(f"Song download error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


async def download_video(link: str) -> Union[str, None]:
    video_id = get_video_id(link)
    if not video_id:
        return None

    ensure_download_dir()
    file_path = f"{DOWNLOAD_DIR}/{video_id}.mp4"

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": "video"}
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=7),
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                token = data.get("download_token")
                if not token:
                    return None

            stream_url = f"{API_URL}/stream/{video_id}?type=video&token={token}"
            async with session.get(
                stream_url,
                timeout=aiohttp.ClientTimeout(total=600),
            ) as fr:
                if fr.status == 302:
                    redirect = fr.headers.get("Location")
                    if not redirect:
                        return None
                    async with session.get(redirect) as rr:
                        if rr.status != 200:
                            return None
                        with open(file_path, "wb") as f:
                            async for chunk in rr.content.iter_chunked(16384):
                                f.write(chunk)

                elif fr.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in fr.content.iter_chunked(16384):
                            f.write(chunk)
                else:
                    return None

        return file_path if os.path.getsize(file_path) > 0 else None

    except Exception as e:
        LOGGER.error(f"Video download error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


# ------------------------------------------------
# YOUTUBE API CLASS
# ------------------------------------------------

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.clean_ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ---------------- CHECK LINK ----------------

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    # ---------------- FETCH URL ----------------

    async def url(self, message: Message) -> Union[str, None]:
        msgs = [message]
        if message.reply_to_message:
            msgs.append(message.reply_to_message)

        for msg in msgs:
            if msg.entities:
                for ent in msg.entities:
                    if ent.type == MessageEntityType.URL:
                        text = msg.text or msg.caption
                        return text[ent.offset : ent.offset + ent.length]
            if msg.caption_entities:
                for ent in msg.caption_entities:
                    if ent.type == MessageEntityType.TEXT_LINK:
                        return ent.url
        return None

    # ---------------- DETAILS ----------------

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        search = VideosSearch(link, limit=1)
        for r in (await search.next())["result"]:
            duration = r["duration"]
            return (
                r["title"],
                duration,
                int(time_to_seconds(duration)) if duration else 0,
                r["thumbnails"][0]["url"].split("?")[0],
                r["id"],
            )

    async def title(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        search = VideosSearch(link, limit=1)
        for r in (await search.next())["result"]:
            return r["title"]

    async def duration(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        search = VideosSearch(link, limit=1)
        for r in (await search.next())["result"]:
            return r["duration"]

    async def thumbnail(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        search = VideosSearch(link, limit=1)
        for r in (await search.next())["result"]:
            return r["thumbnails"][0]["url"].split("?")[0]

    # ---------------- VIDEO ----------------

    async def video(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        file = await download_video(link)
        if file:
            return 1, file
        return 0, "Video download failed"

    # ---------------- PLAYLIST ----------------

    async def playlist(self, link: str, limit: int, user_id, videoid=False) -> List[str]:
        if videoid:
            link = self.listbase + link
        link = link.split("&")[0]

        if Playlist:
            try:
                plist = await Playlist.get(link)
                vids = []
                for v in plist.get("videos", [])[:limit]:
                    if v and v.get("id"):
                        vids.append(v["id"])
                return vids
            except:
                pass

        # yt-dlp fallback
        proc = await asyncio.create_subprocess_shell(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} {link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        return [x for x in out.decode().split("\n") if x]

    # ---------------- TRACK ----------------

    async def track(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        search = VideosSearch(link, limit=1)
        for r in (await search.next())["result"]:
            return (
                {
                    "title": r["title"],
                    "link": r["link"],
                    "vidid": r["id"],
                    "duration_min": r["duration"],
                    "thumb": r["thumbnails"][0]["url"].split("?")[0],
                },
                r["id"],
            )

    # ---------------- FORMATS ----------------

    async def formats(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        ydl = yt_dlp.YoutubeDL({"quiet": True})
        with ydl:
            info = ydl.extract_info(link, download=False)
            fmts = []
            for f in info.get("formats", []):
                try:
                    if "dash" not in str(f.get("format", "")).lower():
                        fmts.append(
                            {
                                "format": f.get("format"),
                                "filesize": f.get("filesize"),
                                "format_id": f.get("format_id"),
                                "ext": f.get("ext"),
                                "format_note": f.get("format_note"),
                                "yturl": link,
                            }
                        )
                except:
                    continue
        return fmts, link

    # ---------------- SLIDER ----------------

    async def slider(self, link: str, query_type: int, videoid=False):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        search = VideosSearch(link, limit=10)
        res = (await search.next()).get("result")
        r = res[query_type]
        return (
            r["title"],
            r["duration"],
            r["thumbnails"][0]["url"].split("?")[0],
            r["id"],
        )

    # ---------------- FINAL DOWNLOAD ----------------

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        **_,
    ) -> Tuple[Union[str, None], bool]:

        if videoid:
            link = self.base + link

        if video:
            file = await download_video(link)
        else:
            file = await download_song(link)

        if file:
            return file, True
        return None, False
