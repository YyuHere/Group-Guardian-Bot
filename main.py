import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141

# 1. أمر التاك المطور (للأعداد الكبيرة)
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # التأكد من رتبة المستخدم
    user_status = (await context.bot.get_chat_member(chat_id, update.effective_user.id)).status
    if user_status not in ['administrator', 'creator']: return

    users = context.chat_data.get("users", [])
    if not users:
        await update.message.reply_text("❌ مفيش أعضاء مسجلين حالياً!")
        return

    # الرسالة اللي هتتبعت مع التاك (لو مفيش، بنحط رسالة افتراضية)
    custom_message = " ".join(context.args) if context.args else "📢 نداء سريع للجميع!"
    
    total_users = len(users)
    await update.message.reply_text(f"⏳ بدأت منشن {total_users} عضو... استنى ثواني.")

    # إرسال المنشن 5 بـ 5 بنظام "التاك المخفي"
    for i in range(0, total_users, 5):
        chunk = users[i:i + 5]
        # منشن مخفي تماماً (عبارة عن حروف غير مرئية تسبب إشعار فقط)
        hidden_mentions = "".join([f"[\u2063](tg://user?id={u['id']})" for u in chunk])
        
        try:
            await context.bot.send_message(
                chat_id, 
                f"{custom_message}{hidden_mentions}", 
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error sending batch: {e}")
            await asyncio.sleep(2) # لو حصل ضغط نريح شوية

        # سرعة ذكية: بعد كل رسالة ربع ثانية، ولو كملنا 50 رسالة نريح ثانية كاملة
        await asyncio.sleep(0.3)
        if (i // 5) % 10 == 0:
            await asyncio.sleep(1)

    await context.bot.send_message(chat_id, "✅ تم المنشن للجميع بنجاح!")

# 2. المعالج الشامل (المنع، التسجيل، والنقل الفوري)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # أ - تسجيل العضو للمنشن
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u and not any(user['id'] == u.id for user in context.chat_data["users"]):
        context.chat_data["users"].append({"id": u.id, "name": u.first_name})

    # ب - منع الروابط (لغير الأدمن)
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if res.status not in ['administrator', 'creator']:
            try:
                await update.message.delete()
                return
            except: pass

    # ج - نقل الميديا (صور وفيديوهات) فوراً للمخزن
    if update.message.photo or update.message.video:
        try:
            await context.bot.copy_message(
                chat_id=TARGET_GROUP_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"Error in forwarding: {e}")

def main():
    if not TOKEN: 
        print("خطأ: BOT_TOKEN غير موجود!")
        return
        
    app = Application.builder().token(TOKEN).build()
    
    # الأوامر
    app.add_handler(CommandHandler("all", tag_all))
    
    # مراقبة كل شيء (نصوص وميديا)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال دلوقتي..")
    app.run_polling()

if __name__ == '__main__':
    main()
