import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')

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

# تسجيل الأعضاء لما يتكلموا
async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    info = {"id": u.id, "name": u.first_name}
    if info not in context.chat_data["users"]: context.chat_data["users"].append(info)

# 2. منع الروابط
async def no_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    if re.search(r'http[s]?://|www\.', update.message.text):
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if m.status not in ['administrator', 'creator']:
            try:
                await update.message.delete()
                await context.bot.send_message(update.effective_chat.id, f"⚠️ ممنوع الروابط يا {update.effective_user.first_name}!")
            except: pass

# 3. أمر سحب الميديا
async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if m.status not in ['administrator', 'creator']: return
    await update.message.reply_text("البوت هيسحب الميديا الجديدة اللي هتنزل في الجروب ويبعتها!")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("all", tag_all))
    app.add_handler(CommandHandler("getmedia", get_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, no_links))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect))
    app.run_polling()

if __name__ == '__main__':
    main()
