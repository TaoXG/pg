import logging
import os
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application as TelegramApplication, CommandHandler, MessageHandler, filters
from http import HTTPStatus
from dashscope import Application

BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_ID = os.getenv('DASHSCOPE_APP_ID')
API_KEY = os.getenv('DASHSCOPE_API_KEY')

keywords = ['alist', 'tvbox', '4567', '小雅', '独立版', '纯净版', '集成版', '?', '？']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context):
    await update.message.reply_text('Hello! Send me a message, and I will reply.')


def contains_keywords(message: str):
    if 'commit' in message:
        return False
    return any(keyword in message.lower() for keyword in keywords)  # Convert to lowercase for case-insensitive matching


async def handle_message(update: Update, context):
    user_message = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    user_first_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name if update.message.from_user.last_name else ''
    full_name = f"{user_first_name} {user_last_name}".strip()
    channel_name = update.message.chat.title
    channel_id = update.message.chat.id

    logger.info(f"From channel {channel_id} '{channel_name}' user {user_id} @{username} '{full_name}', received message: {user_message}")
    if user_message == "中文文档":
        await update.message.reply_text("https://github.com/power721/alist-tvbox/blob/master/doc/README_zh.md")
    #if (len(user_message) > 4 and contains_keywords(user_message)) or channel_name is None:
    elif len(user_message) > 4 and user_message.startswith("求助"):
        response = Application.call(app_id=APP_ID, prompt=user_message, api_key=API_KEY)
        if response.status_code != HTTPStatus.OK:
            print(
                'request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
        else:
            print('request_id=%s\n output=%s\n usage=%s\n' % (response.request_id, response.output, response.usage))
            try:
                await update.message.reply_markdown(response.output.text)
            except BadRequest:
                await update.message.reply_text(response.output.text)


def main():
    application = TelegramApplication.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
