import os, re, asyncio
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# ================= الإعدادات الأساسية =================
TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406 
GROUPS_FILE = "bot_groups.txt"
# =================================================

# دالة لحفظ أيدي الجروب في ملف نصي لضمان عدم ضياع البيانات
def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

# دالة لقراءة الجروبات التي تم تسجيلها
def get_tracked_groups():
    if not os.path.exists(GROUPS_FILE): return []
    with open(GROUPS_FILE, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]

# 1. وظيفة مراقبة المشرفين (سحب الرتب فوراً عند الطرد)
async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    result = update.chat_member
    if not result: return
    
    # لو حد اتحظر أو طرد
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        # لو اللي طرد مش أنت ومش البوت نفسه
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
                # تجريد المشرف من كل صلاحياته فوراً
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

# 2. وظيفة حماية البوتات (منع إضافة بوتات غريبة)
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            # لو العضو الجديد بوت مش البوت بتاعنا
            if member.is_bot and member.id != context.bot.id:
                # لو اللي ضافه مش أنت
                if update.message.from_user.id != MY_USER_ID:
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                    except: pass

# 3. المعالج العام (منع الروابط + حفظ المجموعات)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    if not update.message or not update.message.text: return
    
    # منع الروابط لغير الأدمن
    if re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            try:
                await update.message.delete()
            except: pass

# 4. أمر جلب الروابط (خاص بك أنت فقط)
async def get_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق من أن مرسل الأمر هو صاحب الأيدي الخاص بك
    if update.effective_user.id != MY_USER_ID:
        return
    
    chat_ids = get_tracked_groups()
    if not chat_ids:
        await update.message.reply_text("📭 لم يتم تسجيل أي مجموعات في القائمة حتى الآن.")
        return
        
    await update.message.reply_text("🔄 جاري فحص المجموعات وتجهيز الروابط...")
    
    report = "📋 **قائمة المجموعات المشترك بها البوت:**\n\n"
    
    for cid in chat_ids:
        try:
            chat = await context.bot.get_chat(cid)
            link = chat.invite_link
            
            # إذا لم يكن هناك رابط افتراضي، سيقوم البوت بإنشاء رابط دعوة جديد
            # (يتطلب أن يكون البوت مشرفاً في المجموعة ويمتلك صلاحية إضافة مستخدمين)
            if not link:
                try:
                    invite_obj = await context.bot.create_chat_invite_link(chat_id=cid, name="رابط تحكم المطور")
                    link = invite_obj.invite_link
                except:
                    link = "❌ (لا يمكن جلب الرابط؛ تأكد أن البوت مشرف ولديه صلاحية الروابط)"
            
            report += f"👥 **{chat.title}**\n🆔 `{cid}`\n🔗 {link}\n\n"
        except Exception:
            # في حال قام أحدهم بطرد البوت نهائياً من الجروب
            report += f"🗑️ **مجموعة غير متاحة**\n🆔 `{cid}`\n❌ البوت لم يعد عضواً في هذا الجروب.\n\n"
            
    # تقسيم الرسالة إذا كانت طويلة جداً لأن تليجرام يسمح بـ 4096 حرف كحد أقصى للرسالة الواحدة
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(report, parse_mode="Markdown")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # أمر جلب الروابط للأدمن
    app.add_handler(CommandHandler("links", get_all_links))
    
    # مراقب المشرفين
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    
    # حماية من البوتات
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    
    # منع الروابط والمعالج العام
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. تم إضافة ميزة جلب الروابط عبر أمر /links بنجاح.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
