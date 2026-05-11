import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141

# 1. أمر التاك (الذي يحفز إشعارات تليجرام الرسمية للجميع)
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # التأكد من رتبة المستخدم (لازم يكون أدمن)
    user_status = (await context.bot.get_chat_member(chat_id, update.effective_user.id)).status
    if user_status not in ['administrator', 'creator']: return

    # الرسالة المخصصة
    msg = " ".join(context.args) if context.args else "📢 نداء عاجل للجميع!"
    
    await update.message.reply_text("🚀 جاري تنبيه الـ 600 عضو... استعد!")

    # إرسال 3 رسائل سريعة تحتوي على المنشن الجماعي الرسمي
    # وضعنا @all و @everyone و @online لضمان وصول الإشعار لكل أنواع الحسابات
    for _ in range(3):
        # بنحط المنشنز في سطر لوحده مخفي عشان ميبقاش شكل الرسالة وحش
        magic_tags = "@all @everyone @online"
        await context.bot.send_message(
            chat_id, 
            f"**{msg}**\n\n`{magic_tags}`", 
            parse_mode='Markdown'
        )
        await asyncio.sleep(0.8)

    await context.bot.send_message(chat_id, "✅ تم إرسال التنبيه للكل!")

# 2. المعالج الشامل (نقل ميديا + منع روابط)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # تسجيل العضو (احتياطي للمنشن اليدوي لو حبيت)
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u and not any(user['id'] == u.id for user in context.chat_data["users"]):
        context.chat_data["users"].append({"id": u.id, "name": u.first_name})

    # منع الروابط لغير الأدمن
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if res.status not in ['administrator', 'creator']:
            try:
                await update.message.delete()
                return
            except: pass

    # نقل الميديا للمستودع فوراً
    if update.message.photo or update.message.video:
        try:
            await context.bot.copy_message(
                chat_id=TARGET_GROUP_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except: pass

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("all", tag_all))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال بأقوى نظام تاك..")
    app.run_polling()

if __name__ == '__main__':
    main()
