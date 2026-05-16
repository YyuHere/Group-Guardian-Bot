import os, re, asyncio, html
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

# 4. أمر جلب الروابط (مؤمن بالكامل بالـ HTML)
async def get_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق من الأيدي المكتوب في الأعلى
    if update.effective_user.id != MY_USER_ID:
        return
        
    try:
        # إرسال رد فوري للتأكد من استجابة البوت
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
                
                # تنظيف اسم الجروب لمنع كراش الصيغة
                safe_title = html.escape(chat.title)
                report += f"👥 <b>{safe_title}</b>\n🆔 <code>{cid}</code>\n🔗 {link}\n\n"
            except Exception:
                report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n❌ البوت لم يعد عضواً فيها.\n\n"
                
        # حذف رسالة الانتظار وإرسال التقرير النهائي
        await status_msg.delete()
        
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(report, parse_mode="HTML")
            
    except Exception as master_error:
        # لو انهار الكود لأي سبب آخر، سيخبرك بالسبب فوراً
        print(f"Error in links command: {master_error}")
        try:
            await update.message.reply_text(f"❌ حدث خطأ داخلي:\n<code>{html.escape(str(master_error))}</code>", parse_mode="HTML")
        except: pass

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # أمر جلب الروابط للأدمن (يجب أن يكون في البداية)
    app.add_handler(CommandHandler("links", get_all_links))
    
    # مراقب المشرفين
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    
    # حماية من البوتات
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    
    # منع الروابط والمعالج العام
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. تم تفعيل الحماية وأمر /links الآمن بنجاح.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
