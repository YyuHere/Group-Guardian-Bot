import os
import re
import logging
from telegram import Update, MessageEntity
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

seen_users: dict[int, dict] = {}

URL_PATTERN = re.compile(
    r"(https?://|www\.)\S+",
    re.IGNORECASE,
)


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")


async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and not user.is_bot:
        seen_users[user.id] = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
        }


async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can use this command.")
        return

    if not seen_users:
        await update.message.reply_text("No users have been seen in this group yet.")
        return

    users = list(seen_users.values())
    chunk_size = 5

    for i in range(0, len(users), chunk_size):
        chunk = users[i : i + chunk_size]
        mentions = []
        for u in chunk:
            if u["username"]:
                mentions.append(f"@{u['username']}")
            else:
                mentions.append(
                    f'<a href="tg://user?id={u["id"]}">{u["first_name"]}</a>'
                )
        await update.message.reply_text(
            " ".join(mentions),
            parse_mode="HTML",
        )


async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    if await is_admin(update, context):
        return

    if URL_PATTERN.search(message.text):
        try:
            await message.delete()
            warning = await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"{message.from_user.first_name}, links are not allowed in this group.",
            )
        except Exception as e:
            logger.warning("Could not delete message or send warning: %s", e)


async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can use this command.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    await update.message.reply_text(
        "Searching for photos and videos in this chat's recent history... "
        "Note: Telegram bots can only access messages they have received since they joined. "
        "I'll forward everything I've stored."
    )

    media_items = context.bot_data.get("media_store", {}).get(chat_id, [])

    if not media_items:
        await update.message.reply_text(
            "No photos or videos found in my memory. "
            "I can only retrieve media from messages sent after I joined the group."
        )
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=f"Sending {len(media_items)} media item(s) from the group:",
    )

    for item in media_items:
        try:
            if item["type"] == "photo":
                await context.bot.send_photo(chat_id=user_id, photo=item["file_id"])
            elif item["type"] == "video":
                await context.bot.send_video(chat_id=user_id, video=item["file_id"])
        except Exception as e:
            logger.warning("Could not send media to user: %s", e)

    await update.message.reply_text(
        f"Done! Sent {len(media_items)} media item(s) to your DM."
    )


async def store_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    chat_id = message.chat_id

    if "media_store" not in context.bot_data:
        context.bot_data["media_store"] = {}
    if chat_id not in context.bot_data["media_store"]:
        context.bot_data["media_store"][chat_id] = []

    if message.photo:
        file_id = message.photo[-1].file_id
        context.bot_data["media_store"][chat_id].append(
            {"type": "photo", "file_id": file_id}
        )

    if message.video:
        file_id = message.video.file_id
        context.bot_data["media_store"][chat_id].append(
            {"type": "video", "file_id": file_id}
        )


async def combined_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await track_user(update, context)
    await store_media(update, context)
    await anti_link(update, context)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Set it before running the bot."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("all", mention_all))
    app.add_handler(CommandHandler("media", get_media))

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ALL,
            combined_message_handler,
        )
    )

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
