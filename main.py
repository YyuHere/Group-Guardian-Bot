import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141 
MY_USER_ID = 7878629406 

# حالات البوت
WAITING_FOR_SOURCE = 1

# 1. أمر بدء سحب الميديا
async def start_getmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    
    await update.message.reply_text("🔗 تمام يا وحش، ابعتلي دلوقتي رابط الجروب اللي عاوزني أسحب منه الميديا (أو أي رسالة من الجروب ده):")
    context.user_data['state'] = WAITING_FOR_SOURCE

# 2. وظيفة الحماية (طرد البوتات)
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.is_bot and member.id != context.bot.id:
                adder_id = update.message.from_user.id
                if adder_id != MY_USER_ID:
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                        await update.message.reply_text(f"🚫 ممنوع إضافة بوتات غريبة!")
                    except: pass

# 3. أمر التاك
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_status = (await context.bot.get_chat_member(chat_id, update.effective_user.id)).status
    if user_status not in ['administrator', 'creator']: return
    users = context.chat_data.get("users", [])
    if not users:
        await update.message.reply_text("❌ مفيش أعضاء مسجلين!")
        return
    custom_msg = " ".join(context.args) if context.args else "تاك حد جاهز"
    await update.message.reply_text(f"✅ جاري منشن {len(users)} عضو...")
    for i in range(0, len(users), 5):
        chunk = users[i:i + 5]
        mentions = " ، ".join([f"[{u['name']}](tg://user?id={u['id']})" for u in chunk])
        await context.bot.send_message(chat_id, f"{custom_msg}\n{mentions}", parse_mode='Markdown')
        await asyncio.sleep(0.6)

# 4. المعالج الشامل (الرادار + النقل الذكي)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user_id = update.effective_user.id

    # أ - لو البوت مستني منك رابط الجروب المصدر
    if context.user_data.get('state') == WAITING_FOR_SOURCE:
        # بنسجل إن الجروب ده هو المصدر
        context.chat_data['source_chat_id'] = update.message.chat_id
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم ربط الجروب بنجاح! أي ميديا هتنزل هنا هتروح فوراً للمستودع.")
        return

    # ب - تسجيل العضو للتاك
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u and not u.is_bot:
        if not any(user['id'] == u.id for user in context.chat_data["users"]):
            context.chat_data["users"].append({"id": u.id, "name": u.first_name})

    # ج - منع الروابط
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if res.status not in ['administrator', 'creator']:
            try: await update.message.delete()
            except: pass
            return

    # د - نقل الميديا (لو الرسالة جاية من الجروب المصدر اللي حددناه)
    if update.message.chat_id == context.chat_data.get('source_chat_id'):
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
    app.add_handler(CommandHandler("getmedia", start_getmedia)) # الأمر الجديد
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    app.run_polling()

if __name__ == '__main__':
    main()
