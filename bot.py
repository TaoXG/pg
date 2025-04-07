from datetime import datetime
import logging
import json
import os
import re
import hashlib
import subprocess

import requests
from telethon import TelegramClient, events

# Environment variables
API_ID = os.getenv('API_ID')  # Your API ID (from my.telegram.org)
API_HASH = os.getenv('API_HASH')  # Your API Hash (from my.telegram.org)
zoneId = os.getenv('CF_ZONE_ID')
apiKey = os.getenv('CF_API_KEY')
email = os.getenv('CF_EMAIL')
MAX_FILE_SIZE = 200 * 1024 * 1024  # Max file size 200MB
DOWNLOAD_FOLDER = 'downloads'

channels = [2046444460, 2188783347, 1890409212]
# Initialize the TelegramClient
client = TelegramClient("bot", API_ID, API_HASH)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the download folder if it doesn't exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def commit(new_version, version_file):
    with open(version_file, "w") as text_file:
        text_file.write(new_version)
        text_file.flush()
        os.fsync(text_file.fileno())
        logger.info(f'update version: {new_version} for {version_file}')


def purge_cache(file):
    url = f'https://api.cloudflare.com/client/v4/zones/{zoneId}/purge_cache'
    data = {"files": [f"https://har01d.org/{file}.version", f"https://har01d.org/{file}.zip"]}
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Key': apiKey,
        'X-Auth-Email': email,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print('Success:', response.json())
    else:
        print('Error:', response.status_code, response.text)


def md5(path_file):
    checksum = hashlib.md5()

    fd = open(path_file, "rb")
    while True:
        data = fd.read(4096)
        if len(data) == 0:
            break
        checksum.update(data)

    return checksum.hexdigest()


def save_md5(md5sum, file_name):
    with open(file_name, "w") as text_file:
        text_file.write(md5sum)
        text_file.flush()
        os.fsync(text_file.fileno())
        logger.info(f'update md5: {md5sum} for {file_name}')


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

            await client.download_media(message, "pg.zip")
            commit(new_version, "pg.version")

            subprocess.call(["scp", "pg.zip", "pg.version", "root@104.160.46.225:/var/www/html"])
            purge_cache('pg')
        else:
            # 真心20250406-增量包.zip
            match = re.match(r'真心(\d{8})-?(\d)?-增量包.zip', file_name)
            if match:
                new_version = datetime.now().strftime("%Y%m%d-%H%M")
                logger.info(f"New version: {new_version}")

                await client.download_media(message, "zx.zip")
                commit(new_version, "zx.version")

                subprocess.call(["zip", "-d", "zx.zip", "lib/goProxy_armV7", "lib/goProxy_armV7.md5"])
                subprocess.call(["scp", "zx.zip", "zx.version", "root@104.160.46.225:/var/www/html"])
                purge_cache('zx')
            else:
                # 真心20250402-全量包.zip
                match = re.match(r'真心(\d{8})-?(\d)?-全量包.zip', file_name)
                if match:
                    new_version = datetime.now().strftime("%Y%m%d-%H%M")
                    logger.info(f"New version: {new_version}")

                    await client.download_media(message, "zx.base.zip")
                    commit(new_version, "zx.base.version")

                    subprocess.call(["zip", "-d", "zx.zip", "lib/goProxy_armV7", "lib/sing-box-armV7", "lib/tgsou-armV7", "lib/filebrowser-armV7", "lib/alist-armV7"])
                    subprocess.call(["scp", "zx.base.zip", "zx.base.version", "root@104.160.46.225:/var/www/html"])
                    purge_cache('zx.base')
                else:
                    logger.info(f"Ignoring file {file_name}, does not match version pattern.")


# Run the bot
if __name__ == '__main__':
    logger.info("Bot is running...")
    client.start()
    client.run_until_disconnected()
