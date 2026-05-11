import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141

# وظيفة تسجيل الأعضاء الجدد (أول ما يدخلوا الجروب يتقفشوا)
async def record_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "users" not in context.chat_data: context.chat_data["users"] = []
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if not member.is_bot:
                info = {"id": member.id, "name": member.first_name}
                if not any(u['id'] == member.id for u in context.chat_data["users"]):
                    context.chat_data["users"].append(info)

# 1. أمر التاك المطور
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_status = (await context.bot.get_chat_member(chat_id, update.effective_user.id)).status
    if user_status not in ['administrator', 'creator']: return

    users = context.chat_data.get("users", [])
    if not users:
        await update.message.reply_text("❌ البوت لسه معرفش حد، خليهم يتفاعلوا أو ضيف ناس جديدة!")
        return

    custom_message = " ".join(context.args) if context.args else "📢 نداء للجميع!"
    total = len(users)
    await update.message.reply_text(f"⏳ جاري منشن {total} عضو...")

    for i in range(0, total, 5):
        chunk = users[i:i + 5]
        # منشن مخفي تماماً يسبب إشعار فقط
        hidden_tags = "".join([f"[\u2063](tg://user?id={u['id']})" for u in chunk])
        try:
            await context.bot.send_message(chat_id, f"{custom_message}{hidden_tags}", parse_mode='Markdown')
        except:
            await asyncio.sleep(1)
        
        await asyncio.sleep(0.4) # سرعة متوازنة

    await context.bot.send_message(chat_id, "✅ خلصت يا وحش!")

# 2. المعالج الشامل (نقل ميديا + تسجيل + منع روابط)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # تسجيل أي حد بيتكلم (حتى لو نقطة)
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u and not any(user['id'] == u.id for user in context.chat_data["users"]):
        context.chat_data["users"].append({"id": u.id, "name": u.first_name})

    # منع الروابط
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if res.status not in ['administrator', 'creator']:
            try: await update.message.delete()
            except: pass
            return

    # نقل الميديا فوراً
    if update.message.photo or update.message.video:
        try:
            await context.bot.copy_message(chat_id=TARGET_GROUP_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        except: pass

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # أمر التاك
    app.add_handler(CommandHandler("all", tag_all))
    
    # تسجيل الأعضاء الجدد أوتوماتيك (بمجرد دخولهم)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, record_new_member))
    
    # مراقبة الشات ونقل الميديا
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    app.run_polling()

if __name__ == '__main__':
    main()
