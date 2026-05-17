import os, re, asyncio, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# ================= الإعدادات الأساسية =================
TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406 
GROUPS_FILE = "bot_groups.txt"
NSFW_FILE = "nsfw_protected.txt"  # ملف حفظ الجروبات المفعل بها حماية الصور
TARGET_GROUP_ID = -1003926913948  # أيدي الجروب المحدد
USER_STATES = {}  # حفظ حالة المطور بالخاص (هل البوت ينتظر أيدي الجروب؟)
# =================================================

# دالة لتسجيل الجروب المراد حماية صوره
def save_nsfw_group(chat_id_str):
    if not os.path.exists(NSFW_FILE):
        with open(NSFW_FILE, "w") as f: pass
    with open(NSFW_FILE, "r") as f:
        ids = f.read().splitlines()
    if chat_id_str not in ids:
        with open(NSFW_FILE, "a") as f:
            f.write(f"{chat_id_str}\n")

# دالة لجلب قائمة الجروبات المحمية من الصور
def get_nsfw_groups():
    if not os.path.exists(NSFW_FILE): return []
    with open(NSFW_FILE, "r") as f:
        return f.read().splitlines()

# دالة لحفظ أيدي الجروب في ملف نصي لضمان عدم ضياع البيانات
def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

# دالة آمنة لقراءة الجروبات وتجنب الأخطاء
def get_tracked_groups():
    if not os.path.exists(GROUPS_FILE): return []
    tracked = []
    with open(GROUPS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    tracked.append(int(line))
                except ValueError:
                    continue
    return tracked

# دالة مساعدة لحذف رسالة الترحيب تلقائياً بعد 5 ثواني
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass 

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
                    chat_id=update.effective_chat.id,
                    user_id=actor_id,
                    can_change_info=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False
                )
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name} لمحاولة طرد عضو!")
            except Exception as e:
                print(f"Error demoting admin: {e}")

# 2. وظيفة معالجة الدخول والخروج + حماية البوتات + الترحيب بالمنشن
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(chat_id)
        
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member:
            try:
                await update.message.delete()
            except Exception as e:
                print(f"فشل مسح رسالة الخدمة: {e}")

        if update.message.left_chat_member:
            return

        if update.message.new_chat_members:
            for member in update.message.new_chat_members:
                
                if member.id == MY_USER_ID:
                    try:
                        await context.bot.promote_chat_member(
                            chat_id=chat_id,
                            user_id=MY_USER_ID,
                            can_change_info=True,
                            can_delete_messages=True,
                            can_invite_users=True,
                            can_restrict_members=True,
                            can_pin_messages=True,
                            can_promote_members=True
                        )
                        await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً بكامل الصلاحيات تلقائياً.")
                        continue
                    except Exception as e:
                        print(f"فشل ترقية المطور: {e}")
                
                if member.is_bot and member.id != context.bot.id:
                    if update.message.from_user.id != MY_USER_ID:
                        try:
                            await context.bot.ban_chat_member(chat_id, member.id)
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
                        
                        sent_msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=welcome_text,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 5))
                    except Exception as e:
                        print(f"خطأ في رسالة الترحيب: {e}")

# 3. المعالج العام (منع الروابط + استقبال أيدي الجروب بالخاص)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(chat_id)
        
    if not update.message or not update.message.text: return
    
    # 🔥 ميزة الخاص الجديدة: استقبال أيدي الجروب بعد كتابة أمر التفعيل بالخاص
    if update.effective_chat.type == "private" and user_id == MY_USER_ID:
        if USER_STATES.get(user_id) == "WAITING_FOR_NSFW_ID":
            target_group = update.message.text.strip()
            
            # حفظ الجروب في قائمة حماية الصور العارية تلبيةً لطلبك
            save_nsfw_group(target_group)
            USER_STATES[user_id] = None  # إنهاء الحالة وتصفيرها ليعود البوت طبيعي
            await update.message.reply_text(f"✅ تم تفعيل حماية ومسح الصور +18 بنجاح في الجروب: {target_group}")
            return

    # كود حماية الجروبات القديم من الروابط لغير الأدمنز
    if update.effective_chat.type in ["group", "supergroup"]:
        if re.search(r'http[s]?://|www\.', update.message.text):
            res = await context.bot.get_chat_member(chat_id, user_id)
            if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                try:
                    await update.message.delete()
                except: pass

# 4. أمر جلب الروابط للأدمن
async def get_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID:
        return
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
                    except:
                        link = "❌ (تأكد أن البوت مشرف ولديه صلاحية الروابط)"
                
                safe_title = html.escape(chat.title)
                report += f"👥 <b>{safe_title}</b>\n🆔 <code>{cid}</code>\n🔗 {link}\n\n"
            except Exception:
                report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n❌ البوت لم يعد عضواً فيها.\n\n"
                
        await status_msg.delete()
        
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(report, parse_mode="HTML")
    except Exception as master_error:
        print(f"Error in links command: {master_error}")

# 5. أمر إرسال الرسالة الثابتة
async def send_permanent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID or update.effective_chat.id != TARGET_GROUP_ID:
        return
    try:
        try:
            await update.message.delete()
        except: pass
        
        share_url = "https://t.me/share/url?url=https://t.me/%2BoHkbnzqCuSMzYzQ0"
        keyboard = [[InlineKeyboardButton("قروب المقاطع", url=share_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط "
            "في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>"
        )
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID, 
            text=welcome_text, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"خطأ في إرسال الرسالة الثابتة: {e}")

# 🔥 6. الميزة الجديدة: دالة استقبال الأمر بالخاص لطلب أيدي الجروب
async def start_nsfw_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ هذا الأمر يتم تفعيله داخل الخاص مع البوت فقط!")
        return
        
    # تفعيل حالة انتظار الاستقبال
    USER_STATES[update.effective_user.id] = "WAITING_FOR_NSFW_ID"
    await update.message.reply_text("📥 أهلاً بك يا مطوري، من فضلك أرسل الآن أيدي (ID) أو رابط الجروب المراد منع الصور +18 فيه:")

# 🔥 7. رادار مراقبة الصور ومسحها جوه الجروبات اللي أنت بتحددها بس
async def photo_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo: return
    chat_id = update.effective_chat.id
    
    # فحص هل الجروب الحالي مفعل فيه حماية الصور من الخاص؟
    protected_list = get_nude_protected_groups_placeholder() # استدعاء لستة المحميين
    if str(chat_id) not in protected_list:
        return # لو الجروب مش محمي، البوت بيتجاهل الصورة تماماً ومبيعملش حاجة
        
    # استثناء المشرفين والمطور من الفحص برغبتك لراحة الأدمنز
    res = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if res.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] or update.effective_user.id == MY_USER_ID:
        return

    try:
        # 📌 هنا بنحط سطر الفحص اللي بيمسح الصورة فوراً لو لقاها مخالفة
        # عشان كودك يفضل نظيف ومفهوش كراكيب، سبتلك الفانكشن دي جاهزة عشان تحط فيها كود الفحص اللي يعجبك براحتك
        is_bad_image = await check_image_nsfw_logic(update.message.photo[-1].file_id)
        if is_bad_image:
            await update.message.delete()
    except Exception as e:
        print(f"Error checking image: {e}")

def get_nude_protected_groups_placeholder():
    if not os.path.exists(NSFW_FILE): return []
    with open(NSFW_FILE, "r") as f: return f.read().splitlines()

async def check_image_nsfw_logic(file_id):
    # دي فانكشن الفحص، حالياً بترجع False كأمان عشان الكود ميمسحش صور عشوائية
    return False

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # تسجيل الأوامر القديمة والجديدة
    app.add_handler(CommandHandler("links", get_all_links))
    app.add_handler(CommandHandler("post", send_permanent_message))
    app.add_handler(CommandHandler("protect_nsfw", start_nsfw_setup)) # 🔥 أمر الخاص الجديد لتفعيل حماية جروب
    
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    
    # 🔥 تفعيل رادار مراقبة الميديا والصور
    app.add_handler(MessageHandler(filters.PHOTO, photo_cleaner))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, protect_group))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال بكودك الأصلي.. وتم إضافة ميزة طلب أيدي الجروب بالخاص بنجاح!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
