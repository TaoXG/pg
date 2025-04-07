from telethon.sync import TelegramClient
import os

# Environment variables
API_ID = os.getenv('API_ID')  # Your API ID (from my.telegram.org)
API_HASH = os.getenv('API_HASH')  # Your API Hash (from my.telegram.org)

client = TelegramClient("bot", API_ID, API_HASH)

client.start()

channel_name = "alist_tvbox"
channel = client.get_entity(channel_name)
print(f'Channel name: {channel_name}')
print(f'👉 Channel ID: {channel.id}')

client.run_until_disconnected()
