from os import getenv
import requests
import time
from dotenv import load_dotenv
import re
import yt_dlp
import json

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")

url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'

ydl_opts_audio = {
    'format': 'm4a/bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': 'downloads/%(title)s.%(ext)s',
}
ydl_opts_video = {
    'format': 'best[ext=mp4]/best',
    'merge_output_format': 'mp4',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
     }

def extract_links(text):
    global url_pattern
    links = re.findall(url_pattern, text)
    return links

def send_buttons(chat_id):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "audio", "callback_data": "audio"},
                {"text": "video", "callback_data": "video"}
            ],
            [
                {"text": "Cancel", "callback_data": "cancel"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": "Please select audio or video",
        "reply_markup": keyboard
    }
    response = requests.post(url, json=payload)
    return response.json()


def youtube_download_audio(url):
    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = info['requested_downloads'][0]['filepath']
        return file_path

def youtube_download_video(url):
    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
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
                                send_message(chat_id, "send me a youtube link for downloading")
                            if 'youtube.com' in text or 'youtu.be' in text:
                                links = extract_links(text)
                                message_id = send_buttons(chat_id)['result']['message_id']
                                print("buttons sent")
                    if "callback_query" in update:
                        data = update["callback_query"]["data"]
                        user_id = update["callback_query"]["from"]["id"]

                        if data == "audio":
                            print(f"User wants {user_id} audio")
                            file_path = youtube_download_audio(links[-1])
                            upload_file(chat_id,file_path)
                            delete_message(chat_id,message_id)
                        if data == "video":
                            print(f"User wants {user_id} video")
                            file_path = youtube_download_video(links[-1])
                            upload_file(chat_id,file_path)
                            delete_message(chat_id,message_id)
                        if data == "cancel":
                            delete_message(chat_id,message_id)
                            print(f"User {user_id} canceled")


            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
if __name__ == "__main__":
    print("Bot starting...")
    handle_updates()
