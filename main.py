import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات الأساسية
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141  # جروب المستودع بتاعك

# 1. أمر التاك (5 بـ 5)
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    m = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if m.status not in ['administrator', 'creator']: return

    if "users" not in context.chat_data or not context.chat_data["users"]:
        await update.message.reply_text("محدش اتكلم لسه عشان أعمله تاك!")
        return

    users = list(context.chat_data["users"])
    for i in range(0, len(users), 5):
        chunk = users[i:i + 5]
        mentions = " ".join([f"[{u['name']}](tg://user?id={u['id']})" for u in chunk])
        await context.bot.send_message(chat_id, f"📢 نداء للجميع:\n{mentions}", parse_mode='Markdown')
        await asyncio.sleep(1)

# 2. المعالج الشامل (تسجيل + منع روابط + سحب فوري للميديا)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تسجيل العضو (عشان المنشن)
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u:
        info = {"id": u.id, "name": u.first_name}
        if info not in context.chat_data["users"]: context.chat_data["users"].append(info)

    # منع الروابط (لغير المشرفين)
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if m.status not in ['administrator', 'creator']:
            try:
                await update.message.delete()
                return 
            except: pass

    # سحب الميديا فوراً (صور وفيديوهات)
    # ملاحظة: البوت هينقل أي حاجة تتبعت جديدة أو تتحول (Forward) لهنا
    if update.message.photo or update.message.video:
        try:
            # استخدام copy_message عشان يبعتها كرسالة جديدة مش تحويل
            await update.message.copy(chat_id=TARGET_GROUP_ID)
        except Exception as e:
            print(f"فشل في النقل: {e}")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    # الأوامر
    app.add_handler(CommandHandler("all", tag_all))
    
    # مراقبة كل شيء (نصوص وميديا)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال يا يوسف...")
    app.run_polling()

if __name__ == '__main__':
    main()
