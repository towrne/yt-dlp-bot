import re
import sys
import time
import asyncio
import logging
import requests
import yt_dlp

from os import getenv, makedirs
from dotenv import load_dotenv
from database import setup_database, get_links_by_id, store_links_and_get_id

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
CACHE_PATH = "cache"
url_pattern = r"(?:https?:\/\/)?(?:www\.)?(?:music\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|shorts\/|live\/|)?([\w-]{11})(?:\S+)?"
output_template = "downloads/%(title)s.%(ext)s"

makedirs(CACHE_PATH, exist_ok=True)
makedirs("downloads", exist_ok=True)


COMMON_YDL_OPTS = {
    "cachedir": CACHE_PATH,
    "quiet": True,
    "no_warnings": True,
}

QUALITY_OPTIONS = {
    "mp3_high": {
        **COMMON_YDL_OPTS,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_template,
    },
    "mp3_low": {
        **COMMON_YDL_OPTS,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "outtmpl": output_template,
    },
    "video_1080": {
        **COMMON_YDL_OPTS,
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
    },
    "video_720": {
        **COMMON_YDL_OPTS,
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
    },
    "video_480": {
        **COMMON_YDL_OPTS,
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
    },
    "video_360": {
        **COMMON_YDL_OPTS,
        "format": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
    },
}

dp = Dispatcher()


def extract_links(text):
    links = re.findall(url_pattern, text)

    full_links = []
    for link_id in links:
        if len(link_id) == 11:
            full_links.append(f"https://www.youtube.com/watch?v={link_id}")
    return full_links


def get_video_duration(video_url):

    ydl_opts = {
        **COMMON_YDL_OPTS,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get("duration") if info else None
    except Exception as e:
        logging.warning(f"Failed to get duration for {video_url}: {e}")
        return None


def youtube_download(url, quality):
    ydl_opts = QUALITY_OPTIONS[quality].copy()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info and "requested_downloads" in info and info["requested_downloads"]:
                return info["requested_downloads"][0]["filepath"]
            # Fallback для некоторых версий yt-dlp
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"Download failed for {url}: {e}")
        raise


def upload_file(chat_id, file_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as file:
            files = {"document": file}
            data = {"chat_id": chat_id}
            response = requests.post(url, data=data, files=files, timeout=120)
        return response.json()
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return {"ok": False, "description": str(e)}


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        html.bold(
            "Send me a youtube link for downloading, also you can send multiple links in one message"
        )
    )


@dp.message()
async def message_handler(message: Message) -> None:
    text = message.text or ""
    if "youtube.com" in text or "youtu.be" in text:
        links = extract_links(text)
        if not links:
            await message.answer(html.bold("No valid YouTube links found."))
            return
        
        links_id = await store_links_and_get_id(links)

        builder = InlineKeyboardBuilder()
        for option in QUALITY_OPTIONS:
            builder.button(
                text=f"{option.replace('_', ' ')}", callback_data=f"{option}:{links_id}"
            )
        builder.button(text="Cancel", callback_data="cancel")
        builder.adjust(2)

        await message.answer(
            html.bold("Select quality:"), reply_markup=builder.as_markup()
        )


@dp.callback_query()
async def handle_callbacks(callback: CallbackQuery):
    data = callback.data

    if data == "cancel":
        await callback.message.edit_text(html.bold("Action canceled."))
        return

    split_data = data.split(":")
    if len(split_data) != 2:
        await callback.message.edit_text(html.bold("Invalid callback data."))
        return

    quality = split_data[0]
    links_id = split_data[1]

    if quality not in QUALITY_OPTIONS:
        await callback.message.edit_text(html.bold("Unknown quality."))
        return

    links = await get_links_by_id(links_id)
    if not links:
        await callback.message.edit_text(html.bold("Links not found in database."))
        return

    for link in links:
        # Проверка длительности
        duration = get_video_duration(link)
        if duration is None:
            await callback.message.edit_text(
                html.bold(f"Could not fetch info for {link}")
            )
            continue

        # Оценка размера: ~0.4 MB/сек для видео, ~0.15 MB/сек для MP3
        size_factor = 0.15 if quality.startswith("mp3") else 0.4
        approx_size = duration * size_factor

        if approx_size > 512:
            await callback.message.edit_text(
                html.bold(
                    f"File too big for {link}\nApprox: {approx_size:.1f}MB\nMax: 512MB"
                )
            )
            continue

        await callback.message.edit_text(html.bold(f"Downloading: {link}"))
        
        try:
            file_path = youtube_download(link, quality)
            await callback.message.edit_text(html.bold("Uploading..."))
            result = upload_file(callback.message.chat.id, file_path)
            
            if not result.get("ok"):
                await callback.message.edit_text(
                    html.bold(f"Upload failed: {result.get('description', 'Unknown error')}")
                )
            else:
                await callback.message.edit_text(html.bold("Done!"))
                
        except Exception as e:
            logging.exception("Download/upload error")
            await callback.message.edit_text(
                html.bold(f"Error: {type(e).__name__}")
            )


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await setup_database()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
