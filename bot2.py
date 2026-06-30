from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import json
import os
import re
import subprocess

import requests
from telethon import TelegramClient, events

# Environment variables
API_ID = os.getenv('API_ID')  # Your API ID (from my.telegram.org)
API_HASH = os.getenv('API_HASH')  # Your API Hash (from my.telegram.org)
zoneId = os.getenv('CF_ZONE_ID')
apiKey = os.getenv('CF_API_KEY')
email = os.getenv('CF_EMAIL')
TOKEN = os.getenv("GITHUB_TOKEN")
MAX_FILE_SIZE = 200 * 1024 * 1024  # Max file size 200MB
DOWNLOAD_FOLDER = 'downloads'

channels = [2046444460, 2188783347, 1890409212, 1734222246]
# Initialize the TelegramClient
client = TelegramClient("bot", API_ID, API_HASH)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10 * 1024 * 1024,
    backupCount=7
)
logger.addHandler(handler)

# Create the download folder if it doesn't exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def release(zip_file, new_version, repo):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {TOKEN}"
    }

    # 1️⃣ Create a release
    logger.info(f"Creating release {new_version}...")

    release_data = {
        "tag_name": new_version,
        "target_commitish": "main",
        "name": new_version,
        "body": new_version,
        "draft": False,
        "prerelease": False
    }

    r = requests.post(
        f"https://api.github.com/repos/power721/{repo}/releases",
        headers=headers,
        data=json.dumps(release_data)
    )

    if r.status_code not in (200, 201):
        logger.warning(f"❌ Failed to create release: {r.text}")
        return

    release = r.json()
    upload_url = release["upload_url"].split("{")[0]
    logger.info(f"✅ Created release: {release['html_url']}")

    # 2️⃣ Upload ZIP asset
    if not os.path.exists(zip_file):
        logger.warning(f"❌ File not found: {zip_file}")
        return

    logger.info(f"Uploading asset: {zip_file}...")
    with open(zip_file, "rb") as f:
        upload_headers = headers.copy()
        upload_headers["Content-Type"] = "application/zip"

        upload_url = f"{upload_url}?name={os.path.basename(zip_file)}"
        ur = requests.post(upload_url, headers=upload_headers, data=f)

    if ur.status_code not in (200, 201):
        logger.warning(f"❌ Failed to upload asset: {ur.text}")
        return

    logger.info("✅ Uploaded asset successfully.")
    logger.info(f"🔗 Asset URL: {ur.json()['browser_download_url']}")


@client.on(events.NewMessage(chats=channels))
async def downloader(event):
    message = event.message
    channel_name = message.chat.title
    channel_id = message.chat.id
    logger.info(f"From: {channel_id} {channel_name}")
    if message.document:
        file_name = message.file.name
        file_size = message.document.size

        logger.info(f"Received file: {file_name} with size: {file_size} bytes")

        # Check if file exceeds the size limit
        if file_size > MAX_FILE_SIZE:
            logger.info(f"File {file_name} exceeds size limit. Skipping download.")
            return

        match = re.match(r'pg\.(\d{8}-\d{4}).zip', file_name)
        if match:
            new_version = match.group(1)
            logger.info(f"New version: {new_version}")

            await client.download_media(message, file_name)
            release(file_name, new_version, "PG")
            os.remove(file_name)

        else:
            # 真心20250406-增量包.zip
            match = re.match(r'真心(\d{8})-?(\d)?-?增量包.zip', file_name)
            if match:
                new_version = datetime.now().strftime("%Y%m%d-%H%M")
                logger.info(f"New version: {new_version}")
                new_file = f"zx{new_version}.zip"

                await client.download_media(message, new_file)
                release(new_file, new_version, "ZX")
                os.remove(new_file)

            else:
                # 真心20250402-全量包.zip
                # match = re.match(r'真心(\d{8})-?(\d)?-(全量包|完整包).zip', file_name)
                # if match:
                #     new_version = datetime.now().strftime("%Y%m%d-%H%M")
                #     logger.info(f"New version: {new_version}")
                #     new_file = f"zx-{new_version}.zip"
                #
                #     await client.download_media(message, "zx.base.zip")
                #     commit(new_file, "zx.base.zip")
                #
                # else:
                #     logger.info(f"Ignoring file {file_name}, does not match version pattern.")
                logger.info(f"Ignoring file {file_name}, does not match version pattern.")


# Run the bot
if __name__ == '__main__':
    logger.info("Bot is running...")
    client.start()
    client.run_until_disconnected()
