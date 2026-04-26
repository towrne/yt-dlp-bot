# yt-dlp-bot

A Telegram bot for downloading YouTube videos and audio in various qualities.

## Features

- Download YouTube videos in multiple resolutions: 360p, 480p, 720p, 1080p
- Extract audio in MP3 format (128kbps or 192kbps)
- Support for multiple links in a single message
- Size estimation before download (Telegram file limit: 512MB)
- Inline keyboard for quality selection
- SQLite database for temporary link storage

## Requirements

- Python 3.9+
- FFmpeg (for audio extraction and video merging)

## Installation

1. Clone the repository:
```
git clone https://github.com/towrne/yt-dlp-bot.git
cd yt-dlp-bot
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Create a `.env` file:
```
BOT_TOKEN=your_telegram_bot_token_here
```
Get a token from @BotFather on Telegram.

4. Make sure FFmpeg is installed and available in your PATH.

## Usage

1. Start the bot:
```
python main.py
```
2. Send /start to the bot on Telegram.
3. Send a YouTube link (or multiple links in one message).
4. Select the desired quality from the inline keyboard.
5. Wait for the download and upload to complete.

