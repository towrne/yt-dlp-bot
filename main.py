from os import getenv
import requests   
import time
from dotenv import load_dotenv
import re
import yt_dlp
import json
from database import *

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
setup_database()
cookie_file = 'cookies.txt'
url_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:music\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|shorts\/|live\/|)?([\w-]{11})(?:\S+)?'
CACHE_PATH = 'cache/'
os.makedirs(CACHE_PATH, exist_ok=True)
output_template = 'downloads/%(title)s.%(ext)s'

QUALITY_OPTIONS = {
    'mp3_high': {
        'format': 'm4a/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192', 
        }],
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    },
    'mp3_low': {
        'format': 'm4a/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    },

    'video_1080': {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    },
    'video_720': {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    },
    'video_480': {
        'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    },
    'video_360': {
        'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'cachedir': CACHE_PATH
    }
}

def extract_links(text):
    global url_pattern
    links = re.findall(url_pattern, text)
    return links

def send_buttons(chat_id,links_id):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "mp3 high", "callback_data": f"mp3_high:{links_id}"},
                {"text": "mp3 low", "callback_data": f"mp3_low:{links_id}"}
            ],

            [
                {"text": "mp4 1080p", "callback_data": f"video_1080:{links_id}"},
                {"text": "mp4 720p", "callback_data": f"video_720:{links_id}"}
            ],

            [
                {"text": "mp4 480p", "callback_data": f"video_480:{links_id}"},
                {"text": "mp4 360p", "callback_data": f"video_360:{links_id}"}
            ],

            [
                {"text": "Cancel", "callback_data": "cancel"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": "Select quality",
        "reply_markup": keyboard
    }
    response = requests.post(url, json=payload)
    return response.json()

def get_video_duration(video_url,quality):
    ydl_opts = QUALITY_OPTIONS[quality]

    ydl_opts['cookiesfrombrowser'] = ('firefox',)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        if 'duration' in info:
            return info['duration']
    return None

def youtube_download(url,quality):
    ydl_opts = QUALITY_OPTIONS[quality]
 
    ydl_opts['cookiesfrombrowser'] = ('firefox',)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = info['requested_downloads'][0]['filepath']
        return file_path

def upload_file(chat_id, file_path):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': chat_id}
        response = requests.post(url, data=data, files=files)
    return response.json()

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout":30,"offset":offset}
    response = requests.get(url,params = params)
    return response.json()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
            "chat_id": chat_id,
            "text": text 
        }
    response = requests.post(url, json=payload)
    return response.json()

def delete_message(chat_id,message_id):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    response = requests.post(url, json=payload)
    return response.json()

def handle_updates():
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)

            if "result" in updates:
                print("Result!")
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    if "message" in update:
                        message = update["message"]

                        chat_id = message["chat"]["id"]
                        print(chat_id)
                        if "text" in message:
                            text = message["text"]
                            print(f'User {chat_id}:',text)
                            if text.startswith('/start'):
                                send_message(chat_id, "send me a youtube link for downloading, you can send multiple links in one message")
                            if 'youtube.com' in text or 'youtu.be' in text:
                                links = extract_links(text)
                                links_id = store_links_and_get_id(links)
                                message_id = send_buttons(chat_id,links_id)['result']['message_id']
                                print("buttons sent")
                    if "callback_query" in update:
                        data = update["callback_query"]["data"]
                        chat_id = update["callback_query"]["from"]["id"]
                        message_id = update["callback_query"]["message"]["message_id"]
                        delete_message(chat_id,message_id)

                        if data == "cancel":
                            print(f"User {chat_id} canceled")
                        else:

                            print(f"User {chat_id}: {data}")
                            callback_data = data.split(":")
                            links = get_links_by_id(callback_data[1])
                            quality = callback_data[0]
                            for link in links:
                                download_size = get_video_duration(link,quality)*0.4
                                if download_size > 512:
                                    print('file too big:',download_size,'MB')
                                    send_message(chat_id,f'File size too big for {link} (approx {download_size}MB)\nMaximum file size: 512MB (around 20 minutes of video or 6 hours of audio)')
                                else:
                                    send_message(chat_id,'Download started')
                                    file_path = youtube_download(link,quality)
                                    upload_file(chat_id,file_path)


            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
if __name__ == "__main__":
    print("Bot starting...")
    handle_updates()
