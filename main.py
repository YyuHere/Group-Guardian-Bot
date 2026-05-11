import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141
WAITING_FOR_LINK = 1

# 1. أمر التاك (5 بـ 5)
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    if member.status not in ['administrator', 'creator']: return

    if "users" not in context.chat_data or not context.chat_data["users"]:
        await update.message.reply_text("محدش اتكلم لسه عشان أعمله تاك!")
        return

    users = list(context.chat_data["users"])
    for i in range(0, len(users), 5):
        chunk = users[i:i + 5]
        mentions = " ".join([f"[{u['name']}](tg://user?id={u['id']})" for u in chunk])
        await context.bot.send_message(chat_id, f"📢 نداء للجميع:\n{mentions}", parse_mode='Markdown')
        await asyncio.sleep(1)

# 2. منع الروابط وتسجيل الأعضاء وسحب الميديا
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أولاً: تسجيل العضو (عشان المنشن يشتغل)
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u:
        info = {"id": u.id, "name": u.first_name}
        if info not in context.chat_data["users"]: context.chat_data["users"].append(info)

    # ثانياً: منع الروابط (لغير المشرفين)
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if m.status not in ['administrator', 'creator']:
            try:
                await update.message.delete()
                await context.bot.send_message(update.effective_chat.id, f"⚠️ ممنوع الروابط يا {u.first_name}!")
                return # نوقف التنفيذ هنا عشان الرسالة اتحذفت
            except: pass

    # ثالثاً: معالجة رابط الجروب (السحب)
    user_state = context.user_data.get('state')
    if user_state == WAITING_FOR_LINK and update.message.text:
        await update.message.reply_text(f"✅ تم ربط المصدر! أي ميديا هتنزل هنا هتروح فوراً للمستودع.")
        context.user_data['state'] = None
        context.chat_data['scraping_active'] = True
        return

    # رابعاً: نقل الميديا (لو الوضع شغال)
    if context.chat_data.get('scraping_active'):
        if update.message.photo or update.message.video or update.message.document:
            try:
                await update.message.forward(chat_id=TARGET_GROUP_ID)
            except Exception as e:
                print(f"Error forwarding: {e}")

# 1. أمر طلب السحب
async def start_scraping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if m.status not in ['administrator', 'creator']: return
    await update.message.reply_text("🔗 ارسل لي رابط الجروب (أو أي رسالة) لتفعيل السحب من هنا:")
    context.user_data['state'] = WAITING_FOR_LINK

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("all", tag_all))
    app.add_handler(CommandHandler("getmedia", start_scraping))
    
    # المعالج الشامل (بترتيب المنطق)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    app.run_polling()

if __name__ == '__main__':
    main()
