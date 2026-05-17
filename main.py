import os, re, asyncio, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# 📦 مكتبات الحساب المساعد وبث المكالمات الحديثة
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

# ================= الإعدادات الأساسية =================
TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406 
GROUPS_FILE = "bot_groups.txt"
NSFW_FILE = "nsfw_protected.txt"  # ملف حفظ الجروبات المفعل بها حماية الصور
LOCKS_FILE = "photo_locks.txt"    # ملف حفظ الجروبات المقفول فيها الصور حالياً
TARGET_GROUP_ID = -1003926913948  # أيدي الجروب المحدد
USER_STATES = {}  # حفظ حالة المطور بالخاص

# 🔐 جلب بيانات الحساب المساعد من متغيرات Railway بأمان تلقائياً
API_ID_ENV = os.getenv('API_ID')
API_ID = int(API_ID_ENV) if API_ID_ENV and API_ID_ENV.isdigit() else 0
API_HASH = os.getenv('API_HASH')

# تشغيل الحساب المساعد ومحرك المكالمات لو تم ضبط المتغيرات في السيرفر
userbot = Client("helper_session", api_id=API_ID, api_hash=API_HASH) if API_ID and API_HASH else None
call_client = PyTgCalls(userbot) if userbot else None

LAST_VIDEO_PATH = "stream_video.mp4" # مسار حفظ الفيديو المؤقت للبث
# =================================================

# دالة للتحقق هل المستخدم أدمن في الجروب أو هو المطور
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == MY_USER_ID: return True
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

# دوال إدارة قفل وفتح الصور في الملف النصي
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

# دالة لتسجيل الجروب المراد حماية صوره
def save_nsfw_group(chat_id_str):
    if not os.path.exists(NSFW_FILE):
        with open(NSFW_FILE, "w") as f: pass
    with open(NSFW_FILE, "r") as f:
        ids = f.read().splitlines()
    if chat_id_str not in ids:
        with open(NSFW_FILE, "a") as f: f.write(f"{chat_id_str}\n")

# دالة لجلب قائمة الجروبات المحمية من الصور
def get_nsfw_groups():
    if not os.path.exists(NSFW_FILE): return []
    with open(NSFW_FILE, "r") as f: return f.read().splitlines()

# دالة لحفظ أيدي الجروب في ملف نصي
def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")

# دالة آمنة لقراءة الجروبات وتجنب الأخطاء
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

# دالة مساعدة لحذف رسالة الترحيب تلقائياً بعد 5 ثواني
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass 

# 1. وظيفة مراقبة المشرفين (سحب الرتب فوراً عند الطرد)
async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(update.effective_chat.id)
    result = update.chat_member
    if not result: return
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
                await context.bot.promote_chat_member(chat_id=update.effective_chat.id, user_id=actor_id, can_change_info=False, can_post_messages=False, can_edit_messages=False, can_delete_messages=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False, can_promote_members=False)
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name} لمحاولة طرد عضو!")
            except Exception as e: print(f"Error demoting admin: {e}")

# 2. وظيفة معالجة الدخول والخروج + حماية البوتات + الترحيب بالمنشن
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                        await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً بكامل الصلاحيات تلقائياً.")
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
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        safe_name = html.escape(member.first_name)
                        mention_link = f"<a href='tg://user?id={member.id}'>{safe_name}</a>"
                        welcome_text = f"مرحباً بك يا {mention_link}، <b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>"
                        sent_msg = await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 5))
                    except: pass

# 3. المعالج العام (منع الروابط + استقبال أيدي الجروب بالخاص + تحميل فيديوهات البث)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if not update.message: return
    
    # 📥 إذا أرسل المطور فيديو في الخاص، البوت يحمله فوراً لتشغيله في الكول
    if update.effective_chat.type == "private" and user_id == MY_USER_ID and update.message.video:
        status_msg = await update.message.reply_text("📥 jari تحميل الفيديو وتجهيزه للبث على السيرفر...")
        video_file = await context.bot.get_file(update.message.video.file_id)
        await video_file.download_to_drive(LAST_VIDEO_PATH)
        await status_msg.edit_text("✅ تم حفظ الفيديو بنجاح! تقدر دلوقتي تشغل الكول بأمر /start_call جوه الجروب.")
        return

    if not update.message.text: return

    if update.effective_chat.type == "private" and user_id == MY_USER_ID:
        if USER_STATES.get(user_id) == "WAITING_FOR_NSFW_ID":
            target_group = update.message.text.strip()
            save_nsfw_group(target_group)
            USER_STATES[user_id] = None  
            await update.message.reply_text(f"✅ تم تفعيل حماية ومسح الصور +18 بنجاح في الجروب: {target_group}")
            return

    if update.effective_chat.type in ["group", "supergroup"]:
        if re.search(r'http[s]?://|www\.', update.message.text):
            res = await context.bot.get_chat_member(chat_id, user_id)
            if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                try: await update.message.delete()
                except: pass

# 4. أمر جلب الروابط للأدمن
async def get_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    try:
        status_msg = await update.message.reply_text("🔄 جاري فحص المجموعات وتجهيز الروابط...")
        chat_ids = get_tracked_groups()
        if not chat_ids:
            await status_msg.edit_text("📭 لم يتم تسجيل أي مجموعات في القائمة حتى الآن.")
            return
        report = "📋 <b>قائمة المجموعات المشترك بها البوت:</b>\n\n"
        for cid in chat_ids:
            try:
                chat = await context.bot.get_chat(cid)
                link = chat.invite_link
                if not link:
                    try:
                        invite_obj = await context.bot.create_chat_invite_link(chat_id=cid, name="رابط تحكم المطور")
                        link = invite_obj.invite_link
                    except: link = "❌ (تأكد أن البوت مشرف ولديه صلاحية الروابط)"
                safe_title = html.escape(chat.title)
                report += f"👥 <b>{safe_title}</b>\n🆔 <code>{cid}</code>\n🔗 {link}\n\n"
            except: report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n❌ البوت لم يعد عضواً فيها.\n\n"
        await status_msg.delete()
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks: await update.message.reply_text(chunk, parse_mode="HTML")
        else: await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e: print(f"Error in links command: {e}")

# 5. أمر إرسال الرسالة الثابتة
async def send_permanent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID or update.effective_chat.id != TARGET_GROUP_ID: return
    try:
        try: await update.message.delete()
        except: pass
        share_url = "https://t.me/share/url?url=https://t.me/%2BoHkbnzqCuSMzYzQ0"
        keyboard = [[InlineKeyboardButton("قروب المقاطع", url=share_url)]]
        await context.bot.send_message(chat_id=TARGET_GROUP_ID, text="<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e: print(f"خطأ في إرسال الرسالة الثابتة: {e}")

# 6. أمر جلب أيدي الجروب بالخاص
async def start_nsfw_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ هذا الأمر يتم تفعيله داخل الخاص مع البوت فقط!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_NSFW_ID"
    await update.message.reply_text("📥 أهلاً بك يا مطوري، من فضلك أرسل الآن أيدي (ID) أو رابط الجروب المراد منع الصور +18 فيه:")

# الأوامر القديمة: قفل وفتح إرسال الصور جوه الجروب
async def lock_photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    lock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔒 <b>تم قفل إرسال الصور في المجموعة للأعضاء العاديين بنجاح!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

async def unlock_photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    unlock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔓 <b>تم فتح إرسال الصور في المجموعة، مسموح للجميع الآن!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

# 🔥 7. الأوامر الجديدة المتوافقة بالملي مع النسخة الحديثة لبث الفيديو وكتم المنضمين
async def start_video_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    if not call_client:
        await update.message.reply_text("❌ لم يتم إعداد الحساب المساعد بأمان في متغيرات Railway!")
        return
    chat_id = update.effective_chat.id
    if not os.path.exists(LAST_VIDEO_PATH):
        await update.message.reply_text("❌ لم تقم بإرسال أي فيديو للبوت بالخاص أولاً لتشغيله!")
        return
    await update.message.reply_text("🚀 الحساب المساعد يدخل الكول حالاً ويشغل الفيديو كام...")
    try:
        # 🎯 التعديل الجديد: تمرير مسار الفيديو للمكتبة الحديثة مباشرة بدون كراكيب
        await call_client.join_group_call(
            chat_id, 
            MediaStream(LAST_VIDEO_PATH)
        )
        await userbot.set_administrator_privileges(chat_id, userbot.me.id, can_manage_video_chats=True)
    except Exception as e: 
        await update.message.reply_text(f"❌ حدث خطأ أثناء تشغيل الكول: {e}")

async def stop_video_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    if not call_client: return
    try:
        await call_client.leave_group_call(update.effective_chat.id)
        await update.message.reply_text("🛑 تم إيقاف البث ومغادرة الكول بنجاح.")
    except Exception as e: print(f"Error leaving call: {e}")

# 8. رادار ومراقب مسح الصور التلقائي لو الشات معموله قفل (Lock) من الأدمن
async def photo_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo: return
    chat_id = update.effective_chat.id
    if is_photos_locked(chat_id):
        if not await is_user_admin(update, context):
            try: await update.message.delete()
            except: pass

def get_nude_protected_groups_placeholder():
    if not os.path.exists(NSFW_FILE): return []
    with open(NSFW_FILE, "r") as f: return f.read().splitlines()

async def check_image_nsfw_logic(file_id):
    return False

# تحويل الـ main للتشغيل غير المتزامن التوافقي لـ Railway ليعمل البوت والحساب معاً بسلاسة
async def main_async():
    if userbot and call_client:
        await userbot.start()
        await call_client.start()
        print("الحساب المساعد ومحرك المكالمات جاهزين لبث الكام!")
        
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
    
    await app.initialize()
    await app.start()
    print("البوت شغال وجاهز تماماً على سيرفر Railway!")
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    while True: await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main_async())
