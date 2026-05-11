import os, re, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141 
MY_USER_ID = 7878629406  # الأيدي بتاعك يا يوسف

# 1. وظيفة الحماية (طرد البوتات الغريبة)
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # لو فيه أعضاء جدد دخلوا الجروب
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            # لو العضو اللي دخل ده "بوت" مش البوت بتاعنا
            if member.is_bot and member.id != context.bot.id:
                # بنشوف مين اللي ضافه
                adder_id = update.message.from_user.id
                
                # لو اللي ضافه مش أنت (الأيدي بتاعك)
                if adder_id != MY_USER_ID:
                    try:
                        # اطرد البوت فوراً
                        await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                        await update.message.reply_text(f"🚫 ممنوع إضافة بوتات غريبة يا {update.message.from_user.first_name}! المالك فقط من يضيف.")
                    except Exception as e:
                        print(f"Error banning bot: {e}")

# 2. أمر التاك الحقيقي (بالأسماء)
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_status = (await context.bot.get_chat_member(chat_id, update.effective_user.id)).status
    if user_status not in ['administrator', 'creator']: return

    users = context.chat_data.get("users", [])
    if not users:
        await update.message.reply_text("❌ مفيش أعضاء مسجلين حالياً، لازم يتفاعلوا الأول!")
        return

    custom_msg = " ".join(context.args) if context.args else "تاك حد جاهز"
    
    await update.message.reply_text(f"✅ جاري منشن {len(users)} عضو مسجل...")

    # منشن 5 بـ 5 بالأسماء
    for i in range(0, len(users), 5):
        chunk = users[i:i + 5]
        mentions = " ، ".join([f"[{u['name']}](tg://user?id={u['id']})" for u in chunk])
        
        try:
            await context.bot.send_message(
                chat_id, 
                f"{custom_msg}\n{mentions}", 
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.6)
        except:
            await asyncio.sleep(1)

# 3. المعالج الشامل (رادار تسجيل + نقل ميديا + منع روابط)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # تسجيل الشخص في الرادار (عشان المنشن يشتغل بالأسماء)
    if "users" not in context.chat_data: context.chat_data["users"] = []
    u = update.effective_user
    if u and not u.is_bot:
        if not any(user['id'] == u.id for user in context.chat_data["users"]):
            context.chat_data["users"].append({"id": u.id, "name": u.first_name})

    # منع الروابط لغير الأدمن
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if res.status not in ['administrator', 'creator']:
            try: await update.message.delete()
            except: pass
            return

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
    
    # مراقبة دخول البوتات (الحماية)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    
    # مراقبة الشات (الرادار والميديا)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. حماية الجروب مفعلة!")
    app.run_polling()

if __name__ == '__main__':
    main()
