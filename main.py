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

QUALITY_OPTIONS = {
    "mp3_high": {
        "format": "m4a/bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
    "mp3_low": {
        "format": "m4a/bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
    "video_1080": {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
    "video_720": {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
    "video_480": {
        "format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
    "video_360": {
        "format": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "cachedir": CACHE_PATH,
    },
}

dp = Dispatcher()


def extract_links(text):
    global url_pattern
    links = re.findall(url_pattern, text)
    return links


def get_video_duration(video_url, quality):
    ydl_opts = QUALITY_OPTIONS[quality]
    ydl_opts["cookiesfrombrowser"] = ("chromium",)  # TO-DO: fix that
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        if "duration" in info:
            return info["duration"]
    return None


def youtube_download(url, quality):
    ydl_opts = QUALITY_OPTIONS[quality]
    ydl_opts["cookiesfrombrowser"] = ("chromium",)  # TO-DO: fix that
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = info["requested_downloads"][0]["filepath"]
        return file_path


def upload_file(chat_id, file_path):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {"chat_id": chat_id}
        response = requests.post(url, data=data, files=files)
    return response.json()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        html.bold(
            "Send me a youtube link for downloading, also you can send multiple links in one message"
        )
    )


@dp.message()
async def message_handler(message: Message) -> None:
    if "youtube.com" in message.text or "youtu.be" in message.text:
        links = extract_links(message.text)
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
    else:
        split_data = data.split(":")
        links = await get_links_by_id(split_data[1])
        quality = split_data[0]

        for link in links:
            download_size = get_video_duration(link, quality) * 0.4
            if download_size > 512:
                await callback.message.edit_text(
                    html.bold(
                        f"File size too big for {link} (approx {download_size}MB\nMaximum file size: 512MB"
                    )
                )
                continue

            await callback.message.edit_text(html.bold("Download started"))
            file_path = youtube_download(link, quality)
            upload_file(callback.message.chat.id, file_path)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await setup_database()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
