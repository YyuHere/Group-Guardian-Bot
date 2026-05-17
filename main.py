import os, re, asyncio, html, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# ================= الإعدادات الأساسية =================
TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406 
GROUPS_FILE = "bot_groups.txt"
NUDE_GROUPS_FILE = "nude_protected_groups.txt" # ملف الجروبات المحمية من الصور
TARGET_GROUP_ID = -1003926913948  # أيدي جروب الترحيب التلقائي

# 💡 حط هنا الـ API Key بتاعك من موقع تفحيص الصور (مثل Sightengine أو DeepAI)
# كمثال سنستخدم هيكل فحص، ويمكنك تفعيله برابط الـ API الخاص بك بسهولة.
SIGHTENGINE_USER = 'YOUR_USER_ID'
SIGHTENGINE_SECRET = 'YOUR_API_SECRET'
# =================================================

# --- دالة فحص عري الصور عبر API (خفيفة وسريعة جداً) ---
def is_image_nude(image_path):
    try:
        # لو مش مبرمج الـ API حالياً، الدالة هترجع False كأمان عشان البوت ميعلقش
        if SIGHTENGINE_USER == 'YOUR_USER_ID': 
            return False
            
        params = {
            'models': 'nudity-2.0',
            'api_user': SIGHTENGINE_USER,
            'api_secret': SIGHTENGINE_SECRET
        }
        files = {'media': open(image_path, 'rb')}
        response = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)
        output = response.json()
        
        if output.get('status') == 'success':
            # سحب نسب العري من تحليل الذكاء الاصطناعي
            nudity = output.get('nudity', {})
            # لو نسبة الخلاعة أو العري الكامل أعلى من 0.5 (يعني 50%) إذن الصورة عريانة
            if nudity.get('sexual_activity', 0) > 0.5 or nudity.get('erotica', 0) > 0.5:
                return True
        return False
    except Exception as e:
        print(f"خطأ أثناء فحص الصورة برمجياً: {e}")
        return False

# --- دالت حفظ وإدارة جروبات حماية الصور ---
def manage_nude_file(chat_id, action="add"):
    if not os.path.exists(NUDE_GROUPS_FILE):
        with open(NUDE_GROUPS_FILE, "w") as f: pass
        
    with open(NUDE_GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
        
    if action == "add" and str(chat_id) not in ids:
        with open(NUDE_GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")
    elif action == "del" and str(chat_id) in ids:
        ids.remove(str(chat_id))
        with open(NUDE_GROUPS_FILE, "w") as f:
            for i in ids: f.write(f"{i}\n")

def get_nude_protected_groups():
    if not os.path.exists(NUDE_GROUPS_FILE): return []
    with open(NUDE_GROUPS_FILE, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]

# دالة لحفظ أيدي الجروب العام في ملف نصي
def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")

def get_tracked_groups():
    if not os.path.exists(GROUPS_FILE): return []
    with open(GROUPS_FILE, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass 

# 1. وظيفة مراقبة المشرفين (سحب الرتب فوراً عند الطرد)
async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    result = update.chat_member
    if not result: return
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
                await context.bot.promote_chat_member(
                    chat_id=update.effective_chat.id, user_id=actor_id,
                    can_change_info=False, can_post_messages=False, can_edit_messages=False,
                    can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                    can_pin_messages=False, can_promote_members=False
                )
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name} لمحاولة طرد عضو!")
            except Exception as e: print(f"Error demoting admin: {e}")

# 2. وظيفة معالجة الدخول والخروج + حماية البوتات + الترحيب بالمنشن
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(chat_id)
        
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member:
            try: await update.message.delete()
            except: pass

        if update.message.left_chat_member: return

        if update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id == MY_USER_ID:
                    try:
                        await context.bot.promote_chat_member(
                            chat_id=chat_id, user_id=MY_USER_ID,
                            can_change_info=True, can_delete_messages=True, can_invite_users=True,
                            can_restrict_members=True, can_pin_messages=True, can_promote_members=True
                        )
                        await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً بكامل الصلاحيات تلقائياً.")
                        continue
                    except Exception as e: print(f"فشل ترقية المطور: {e}")
                
                if member.is_bot and member.id != context.bot.id:
                    if update.message.from_user.id != MY_USER_ID:
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
                        
                        welcome_text = (
                            f"مرحباً بك يا {mention_link}، "
                            f"<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط "
                            f"في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>"
                        )
                        sent_msg = await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 5))
                    except Exception as e: print(f"خطأ في رسالة الترحيب: {e}")

# 3. المعالج العام (منع الروابط لغير الأدمن)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    if not update.message or not update.message.text: return
    
    if re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            try: await update.message.delete()
            except: pass

# 🔥 4. الميزة الجديدة: معالج فحص ومسح الصور العارية في الجروبات المحددة فقط
async def monitor_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo: return
    chat_id = update.effective_chat.id
    
    # التأكد أن الجروب الحالي مفعل فيه حماية الصور العارية في الخاص
    protected_nude_chats = get_nude_protected_groups()
    if chat_id not in protected_nude_chats:
        return
        
    # استثناء المشرفين والمالك والمطور من الفحص برغبته
    res = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if res.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] or update.effective_user.id == MY_USER_ID:
        return

    try:
        # تحميل النسخة الأعلى جودة من الصورة للفحص
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        temp_path = f"temp_{update.message.message_id}.jpg"
        await photo_file.download_to_drive(temp_path)
        
        # استدعاء دالة الفحص بالذكاء الاصطناعي
        if is_image_nude(temp_path):
            await update.message.delete() # مسح الصورة فوراً لو عريانة
            
        # مسح الصورة المؤقتة من السيرفر فوراً لتوفير مساحة للجروب
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    except Exception as e:
        print(f"خطأ فحص الميديا: {e}")

# 🔥 5. الميزة الجديدة: أوامر التحكم بالخاص لتفعيل وإلغاء حماية الصور العارية بالجروبات
async def toggle_nude_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    
    command = context.args
    if not command:
        await update.message.reply_text(
            "ℹ️ <b>طريقة الاستخدام في الخاص:</b>\n"
            "• لتفعيل جروب: <code>/add_nude -100xxxxxxx</code>\n"
            "• لإلغاء جروب: <code>/del_nude -100xxxxxxx</code>", 
            parse_mode="HTML"
        )
        return
        
    try:
        target_chat = int(command[0])
        cmd_name = update.message.text.split()[0]
        
        if "add_nude" in cmd_name:
            manage_nude_file(target_chat, "add")
            await update.message.reply_text(f"✅ تم تفعيل حماية ومسح الصور العارية بنجاح في الجروب: <code>{target_chat}</code>", parse_mode="HTML")
        elif "del_nude" in cmd_name:
            manage_nude_file(target_chat, "del")
            await update.message.reply_text(f"❌ تم إلغاء حماية الصور العارية في الجروب: <code>{target_chat}</code>", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ عذراً يا غالي، تأكد من كتابة أيدي الجروب بشكل صحيح كأرقام فقط.")

# 6. أمر جلب الروابط للأدمن
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
            except Exception: report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n❌ البوت لم يعد عضواً فيها.\n\n"
                
        await status_msg.delete()
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks: await update.message.reply_text(chunk, parse_mode="HTML")
        else: await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e: print(f"Error links: {e}")

# 7. أمر إرسال الرسالة الثابتة
async def send_permanent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID or update.effective_chat.id != TARGET_GROUP_ID: return
    try:
        try: await update.message.delete()
        except: pass
        share_url = "https://t.me/share/url?url=https://t.me/%2BoHkbnzqCuSMzYzQ0"
        keyboard = [[InlineKeyboardButton("قروب المقاطع", url=share_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_text = "<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>"
        await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e: print(f"Error permanent msg: {e}")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # تسجيل الأوامر
    app.add_handler(CommandHandler("links", get_all_links))
    app.add_handler(CommandHandler("post", send_permanent_message))
    app.add_handler(CommandHandler(["add_nude", "del_nude"], toggle_nude_protection)) # أوامر التحكم بالخاص
    
    # مراقب المشرفين
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    
    # مراقب الميديا (الصور لـ مسح العري)
    app.add_handler(MessageHandler(filters.PHOTO, monitor_photos))
    
    # مراقب الانضمام والمغادرة
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, protect_group))
    
    # المعالج العام للرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. وتم دمج ميزة التحكم بحماية الصور العارية بالخاص وحصرها بجروبات محددة!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
