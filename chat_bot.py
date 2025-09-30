#!/usr/bin/env python3
import logging
import os
from datetime import datetime, timedelta
from http import HTTPStatus

from telegram import Update, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import (
    Application as TelegramApplication,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)
from dashscope import Application as DashscopeApp  # alias to avoid name clash

# Environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_ID = os.getenv("DASHSCOPE_APP_ID")
API_KEY = os.getenv("DASHSCOPE_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Basic command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is alive. I will log updates for debugging.")

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    from_user = update.effective_user

    # 1. Check args
    if not context.args:
        await update.message.reply_text("Usage: /allow <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return

    logger.info("allow user %s to send message in chat %s", user_id, chat_id)
    # 2. Check if the caller is an admin
    member = await context.bot.get_chat_member(chat_id, from_user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ You must be an admin to use this command.")
        logger.warning("Non-admin %s tried to run /allow in chat %s", from_user.id, chat_id)
        return

    # 3. Try to lift the restriction
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=True),
        )

        # cleanup new_members dict
        if chat_id in new_members and user_id in new_members[chat_id]:
            del new_members[chat_id][user_id]
            if not new_members[chat_id]:
                del new_members[chat_id]

        await update.message.reply_text(f"✅ User {user_id} is now allowed to send messages.")
        logger.info("Admin %s allowed user %s in chat %s", from_user.id, user_id, chat_id)

    except BadRequest as e:
        logger.exception("Failed to allow user %s in chat %s: %s", user_id, chat_id, e)
        await update.message.reply_text(f"❌ Failed to unmute user {user_id}: {e.message}")


# Your message handler (kept as-is, but using DashscopeApp alias)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text == "中文文档":
        await update.message.reply_text(
            "https://github.com/power721/alist-tvbox/blob/master/doc/README_zh.md"
        )
        return
    if len(text) > 4 and (text.startswith("求助") or text.startswith("请教") or "@alist_tvbox_bot" in text):
        response = DashscopeApp.call(app_id=APP_ID, prompt=text, api_key=API_KEY)
        if response.status_code != HTTPStatus.OK:
            logger.error("dashscope error: %s %s", response.status_code, getattr(response, "message", None))
        else:
            try:
                await update.message.reply_markdown(response.output.text)
            except BadRequest:
                await update.message.reply_text(response.output.text)


delay_hours = 6
new_members = {}


def record_new_member(chat_id: int, user_id: int):
    join_time = datetime.now()
    if chat_id not in new_members:
        new_members[chat_id] = {}
    new_members[chat_id][user_id] = join_time
    logger.info("Recorded new member: chat=%s user=%s at %s", chat_id, user_id, join_time)


def joined_within(chat_id: int, user_id: int, minutes: int = 3) -> bool:
    """Return True if the user joined within the last `minutes` minutes."""
    if chat_id not in new_members or user_id not in new_members[chat_id]:
        return False
    join_time = new_members[chat_id][user_id]
    return datetime.now() - join_time <= timedelta(minutes=minutes)


# Handler when the message contains new_chat_members (typical, fires on someone joining)
async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        logger.info("Detected new_chat_member via message: %s in chat %s", member.to_dict(), chat_id)
        # mute for 24 hours
        # until = datetime.utcnow() + timedelta(hours=delay_hours)
        # try:
        #     await context.bot.restrict_chat_member(
        #         chat_id=chat_id,
        #         user_id=member.id,
        #         permissions=ChatPermissions(can_send_messages=False),
        #         until_date=until,
        #     )
        #     # await update.effective_chat.send_message(
        #     #     f"👋 Welcome {member.full_name}! You are muted for {delay_hours} hours."
        #     # )
        # except BadRequest as e:
        #     logger.exception("Failed to restrict member %s: %s", member.id, e)


# ChatMember status change handler (fired when status fields change)
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # logging for debugging
    try:
        logger.debug("ChatMember update event: %s", update.chat_member.to_dict())
    except Exception:
        logger.info("ChatMember update (no to_dict available)")
    # check for a join via status change: left/kicked -> member
    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status
    user = update.chat_member.new_chat_member.user
    chat = update.chat_member.chat
    logger.info("chat_member status: %s -> %s for user %s in chat %s", old_status, new_status, user, chat)
    if old_status in ("left", "kicked") and new_status == "member":
        record_new_member(chat.id, user.id)
    if old_status == "restricted" and new_status == "member":
        if joined_within(chat.id, user.id):
            await restrict_chat_member(context, chat.id, user.id)
        del new_members[chat.id][user.id]


async def restrict_chat_member(context: ContextTypes.DEFAULT_TYPE, chat_id, user_id):
    until = datetime.now() + timedelta(hours=delay_hours)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        logger.info("restrict_chat_member for user %s in chat %s", user_id, chat_id)
        # await context.bot.send_message(chat.id, f"👋 Welcome {user.full_name}! You are muted for {delay_hours} hours.")
    except BadRequest as e:
        logger.exception("Failed to restrict via chat_member handler for user %s: %s", user_id, e)


# Generic debug logger for messages (added last so it doesn't interfere)
async def debug_message_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # be careful: big dicts — logger prints compact form
        logger.info("DEBUG UPDATE (message): %s", update.to_dict())
    except Exception:
        logger.info("Received update (non-serializable): %s", update)


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN env var not set")
        return

    app = TelegramApplication.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # app.add_handler(CommandHandler("allow", allow))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # NEW_CHAT_MEMBERS messages
    #app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    # ChatMember status updates
    app.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    # Generic logger (low priority/group so it runs after others)
    #app.add_handler(MessageHandler(filters.ALL, debug_message_logger), group=100)

    # Run polling WITHOUT restricting allowed_updates (default None -> receive everything)
    logger.info("Starting polling. Telegram lib version: %s", getattr(__import__("telegram"), "__version__", "unknown"))
    app.run_polling()  # if you use webhook, ensure allowed_updates includes ["message","chat_member"]


if __name__ == "__main__":
    main()
